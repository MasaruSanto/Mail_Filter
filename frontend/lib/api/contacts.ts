import { apiFetch } from "./client";

export type Contact = { name: string; email: string };

export function getContacts(token: string): Promise<Contact[]> {
  return apiFetch<Contact[]>("/api/v1/contacts", {
    headers: { Authorization: `Bearer ${token}` },
  });
}
