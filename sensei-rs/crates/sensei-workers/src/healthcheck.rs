/// Perform the `--healthcheck` probe: connect to PostgreSQL (when
/// configured) and NATS JetStream, and report readiness. Never blocks on
/// retries — a single attempt with a short timeout decides.
pub fn runtime_healthcheck() -> i32 {
    use std::time::Duration;

    let rt = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(rt) => rt,
        Err(_) => return 1,
    };

    rt.block_on(async {
        // NATS (required): a real JetStream publish/ack round-trip.
        let nats_url =
            std::env::var("NATS_URL").unwrap_or_else(|_| "nats://localhost:4222".to_string());
        let mut options =
            async_nats::ConnectOptions::default().connection_timeout(Duration::from_secs(5));
        if let Ok(token) = std::env::var("NATS_TOKEN") {
            if !token.is_empty() {
                options = options.token(token);
            }
        }
        let client =
            match tokio::time::timeout(Duration::from_secs(8), options.connect(&nats_url)).await {
                Ok(Ok(client)) => client,
                _ => {
                    eprintln!("HEALTHCHECK: NATS unreachable at {nats_url}");
                    return 1;
                }
            };
        let js = async_nats::jetstream::new(client);
        match js.publish("sensei.health".to_string(), "ok".into()).await {
            Ok(ack) => {
                if ack.await.is_err() {
                    eprintln!("HEALTHCHECK: NATS JetStream publish not acknowledged");
                    return 1;
                }
            }
            Err(e) => {
                eprintln!("HEALTHCHECK: NATS JetStream publish failed: {e}");
                return 1;
            }
        }
        drop(js);

        // PostgreSQL (when configured): SELECT 1.
        if let Ok(url) = std::env::var("DATABASE_URL") {
            if !url.is_empty() {
                let pool = match sqlx::postgres::PgPoolOptions::new()
                    .max_connections(2)
                    .acquire_timeout(Duration::from_secs(5))
                    .connect(&url)
                    .await
                {
                    Ok(p) => p,
                    Err(e) => {
                        eprintln!("HEALTHCHECK: PostgreSQL unreachable: {e}");
                        return 1;
                    }
                };
                if sqlx::query_scalar::<_, i32>("SELECT 1")
                    .fetch_one(&pool)
                    .await
                    .is_err()
                {
                    eprintln!("HEALTHCHECK: PostgreSQL SELECT 1 failed");
                    return 1;
                }
            }
        }

        eprintln!("HEALTHCHECK: ok");
        0
    })
}
