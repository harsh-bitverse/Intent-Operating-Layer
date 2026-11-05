import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || 'http://127.0.0.1:8000';

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleProxy(request, params.path);
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleProxy(request, params.path);
}

export async function PUT(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleProxy(request, params.path);
}

export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleProxy(request, params.path);
}

async function handleProxy(request: NextRequest, pathSegments: string[]) {
  const subpath = pathSegments.join('/');
  const search = request.nextUrl.search;
  const targetUrl = `${BACKEND_URL}/api/${subpath}${search}`;

  const forwardHeaders = new Headers();
  request.headers.forEach((val, key) => {
    // Avoid forwarding host or conflicting connection headers
    if (!['host', 'connection', 'content-length'].includes(key.toLowerCase())) {
      forwardHeaders.set(key, val);
    }
  });

  const isSSE = request.headers.get('accept')?.includes('text/event-stream');

  try {
    const fetchOptions: RequestInit = {
      method: request.method,
      headers: forwardHeaders,
      // @ts-ignore - duplex is valid in Node 18+ fetch
      duplex: 'half',
    };

    if (request.method !== 'GET' && request.method !== 'HEAD') {
      const body = await request.arrayBuffer();
      if (body.byteLength > 0) {
        fetchOptions.body = body;
      }
    }

    const res = await fetch(targetUrl, fetchOptions);

    if (isSSE || res.headers.get('content-type')?.includes('text/event-stream')) {
      return new NextResponse(res.body, {
        status: res.status,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-transform',
          'Connection': 'keep-alive',
          'X-Accel-Buffering': 'no',
        },
      });
    }

    const data = await res.arrayBuffer();
    const responseHeaders = new Headers();
    res.headers.forEach((val, key) => {
      responseHeaders.set(key, val);
    });

    return new NextResponse(data, {
      status: res.status,
      headers: responseHeaders,
    });
  } catch (err: any) {
    return NextResponse.json(
      { error: 'BFF proxy failed to connect to backend', detail: err.message },
      { status: 502 }
    );
  }
}
