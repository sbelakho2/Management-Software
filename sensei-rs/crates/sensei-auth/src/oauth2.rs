//! OAuth2/OIDC client for third-party authentication providers.
//!
//! Supports standard OAuth2 authorization code flow with providers like
//! Google, Microsoft Azure AD, GitHub, and any OpenID Connect provider.

use oauth2::{
    AuthUrl, AuthorizationCode, ClientId, ClientSecret, CsrfToken,
    PkceCodeChallenge, RedirectUrl, Scope, TokenUrl,
};
use oauth2::basic::BasicClient;
use oauth2::url::Url;
use sensei_core::error::{Result, SenseiError};

pub use sensei_core::config::OAuth2ProviderConfig;

/// The OAuth2 client for interacting with providers.
///
/// Stores the config separately and builds the oauth2 client on demand
/// to work around the complex type-level state machine in the oauth2 crate.
pub struct OAuth2Client {
    config: OAuth2ProviderConfig,
}

impl OAuth2Client {
    /// Create a new [`OAuth2Client`] from the given configuration.
    pub fn new(config: OAuth2ProviderConfig) -> Self {
        Self { config }
    }

    /// Create a new [`OAuth2Client`] from a configuration, validating that
    /// the authorization, token, and redirect URLs are well-formed.
    pub fn from_config(config: &OAuth2ProviderConfig) -> Result<Self> {
        AuthUrl::new(config.auth_url.clone())
            .map_err(|e| SenseiError::Configuration(format!("Invalid auth URL: {e}")))?;
        TokenUrl::new(config.token_url.clone())
            .map_err(|e| SenseiError::Configuration(format!("Invalid token URL: {e}")))?;
        RedirectUrl::new(config.redirect_url.clone())
            .map_err(|e| SenseiError::Configuration(format!("Invalid redirect URL: {e}")))?;

        Ok(Self::new(config.clone()))
    }

    /// Generate the authorization URL for the OAuth2 flow.
    ///
    /// Returns the URL to redirect the user to, along with the CSRF token
    /// and PKCE verifier that must be stored in the session.
    pub fn authorization_url(&self) -> Result<(Url, CsrfToken, oauth2::PkceCodeVerifier)> {
        let auth_url = AuthUrl::new(self.config.auth_url.clone())
            .map_err(|e| SenseiError::Configuration(format!("Invalid auth URL: {e}")))?;

        let redirect_url = RedirectUrl::new(self.config.redirect_url.clone())
            .map_err(|e| SenseiError::Configuration(format!("Invalid redirect URL: {e}")))?;

        let client = BasicClient::new(ClientId::new(self.config.client_id.clone()))
            .set_client_secret(ClientSecret::new(self.config.client_secret.clone()))
            .set_auth_uri(auth_url)
            .set_redirect_uri(redirect_url);

        let (pkce_challenge, pkce_verifier) = PkceCodeChallenge::new_random_sha256();

        let mut auth_request = client
            .authorize_url(CsrfToken::new_random)
            .set_pkce_challenge(pkce_challenge);

        for scope in &self.config.scopes {
            auth_request = auth_request.add_scope(Scope::new(scope.clone()));
        }

        let (url, csrf_token) = auth_request.url();

        Ok((url, csrf_token, pkce_verifier))
    }

    /// Exchange an authorization code for tokens.
    ///
    /// # Arguments
    /// * `code` - The authorization code received from the provider.
    /// * `pkce_verifier` - The PKCE verifier generated during authorization URL creation.
    ///
    /// # Returns
    /// The OAuth2 token response containing access and refresh tokens.
    pub async fn exchange_code(
        &self,
        code: String,
        pkce_verifier: oauth2::PkceCodeVerifier,
    ) -> Result<oauth2::StandardTokenResponse<oauth2::EmptyExtraTokenFields, oauth2::basic::BasicTokenType>> {
        let token_url = TokenUrl::new(self.config.token_url.clone())
            .map_err(|e| SenseiError::Configuration(format!("Invalid token URL: {e}")))?;

        let redirect_url = RedirectUrl::new(self.config.redirect_url.clone())
            .map_err(|e| SenseiError::Configuration(format!("Invalid redirect URL: {e}")))?;

        let client = BasicClient::new(ClientId::new(self.config.client_id.clone()))
            .set_client_secret(ClientSecret::new(self.config.client_secret.clone()))
            .set_token_uri(token_url)
            .set_redirect_uri(redirect_url);

        let http_client = reqwest::Client::new();

        client
            .exchange_code(AuthorizationCode::new(code))
            .set_pkce_verifier(pkce_verifier)
            .request_async(&http_client)
            .await
            .map_err(|e| SenseiError::ExternalService(format!("OAuth2 token exchange failed: {e}")))
    }

    /// Refresh an access token using a refresh token.
    pub async fn refresh_token(
        &self,
        refresh_token: &str,
    ) -> Result<oauth2::StandardTokenResponse<oauth2::EmptyExtraTokenFields, oauth2::basic::BasicTokenType>> {
        let token_url = TokenUrl::new(self.config.token_url.clone())
            .map_err(|e| SenseiError::Configuration(format!("Invalid token URL: {e}")))?;

        let redirect_url = RedirectUrl::new(self.config.redirect_url.clone())
            .map_err(|e| SenseiError::Configuration(format!("Invalid redirect URL: {e}")))?;

        let client = BasicClient::new(ClientId::new(self.config.client_id.clone()))
            .set_client_secret(ClientSecret::new(self.config.client_secret.clone()))
            .set_token_uri(token_url)
            .set_redirect_uri(redirect_url);

        let http_client = reqwest::Client::new();

        client
            .exchange_refresh_token(&oauth2::RefreshToken::new(refresh_token.to_string()))
            .request_async(&http_client)
            .await
            .map_err(|e| SenseiError::ExternalService(format!("Token refresh failed: {e}")))
    }
}
