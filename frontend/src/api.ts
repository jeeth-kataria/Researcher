let ownerToken = "";
export function setOwnerToken(token: string) {
  ownerToken = token;
}
export async function request(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers);
  if (ownerToken) headers.set("Authorization", `Bearer ${ownerToken}`);
  if (typeof options.body === "string")
    headers.set("Content-Type", "application/json");
  const response = await fetch("/api" + path, { ...options, headers });
  if (!response.ok) {
    let detail = `${response.status}: request failed`;
    try {
      const body = await response.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
    } catch {
      /* Preserve status for unavailable backend. */
    }
    throw new Error(detail);
  }
  return response;
}
export async function api(path: string, options: RequestInit = {}) {
  return (await request(path, options)).json();
}
export function download(text: string, name: string) {
  const url = URL.createObjectURL(
    new Blob([text], { type: "text/markdown;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
