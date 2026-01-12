export const runtime = 'nodejs';

export async function GET(): Promise<Response> {
  return Response.json(
    {
      status: 'ok',
      timestamp: new Date().toISOString(),
    },
    { status: 200 }
  );
}
