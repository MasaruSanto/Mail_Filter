import { apiFetch } from "./client";
import type { CalendarEvent } from "@/lib/types/api";

export type CalendarEventInput = {
  summary: string;
  start: string;
  end: string;
  location?: string;
  description?: string;
};

function authHeaders(token: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export const getCalendarEvents = (token: string): Promise<CalendarEvent[]> =>
  apiFetch<CalendarEvent[]>("/api/v1/calendar/events", {
    headers: authHeaders(token),
  });

export const createCalendarEvent = (
  token: string,
  body: CalendarEventInput,
): Promise<CalendarEvent> =>
  apiFetch<CalendarEvent>("/api/v1/calendar/events", {
    method: "POST",
    body: JSON.stringify(body),
    headers: authHeaders(token),
  });

export const updateCalendarEvent = (
  token: string,
  eventId: string,
  body: CalendarEventInput,
): Promise<CalendarEvent> =>
  apiFetch<CalendarEvent>(`/api/v1/calendar/events/${eventId}`, {
    method: "PUT",
    body: JSON.stringify(body),
    headers: authHeaders(token),
  });

export const deleteCalendarEvent = (
  token: string,
  eventId: string,
): Promise<void> =>
  apiFetch<void>(`/api/v1/calendar/events/${eventId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
