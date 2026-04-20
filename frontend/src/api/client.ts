export class ApiError extends Error {
    constructor(
        public readonly status: number,
        message: string,
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

export async function apiFetch<T>(
    path: string,
    options?: RequestInit,
): Promise<T> {
    const res = await fetch(path, options);

    if (!res.ok) {
        let message = `HTTP ${res.status}`;
        try {
            const body = await res.json();
            message = body?.error?.message ?? message;
        } catch {
            // ignore parse errors — keep the default message
        }
        throw new ApiError(res.status, message);
    }

    return res.json() as Promise<T>;
}
