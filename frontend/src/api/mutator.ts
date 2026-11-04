export const customFetch = async <T>(url: string, options?: RequestInit): Promise<T> => {
  const baseUrl = import.meta.env.VITE_API_URL;
  if (!baseUrl) throw new Error('VITE_API_URL is not set (frontend/.env.local)');
  const response = await fetch(`${baseUrl}${url}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw Object.assign(new Error(body.detail ?? 'Request failed'), {
      status: response.status,
      data: body,
    });
  }
  return response.json() as Promise<T>;
};
