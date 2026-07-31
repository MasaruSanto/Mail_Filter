"use client";

import { useState, useMemo } from "react";
import type { CalendarEvent } from "@/lib/types/api";
import {
  createCalendarEvent,
  updateCalendarEvent,
  deleteCalendarEvent,
  type CalendarEventInput,
} from "@/lib/api/calendar";

const WEEKDAYS = ["日", "月", "火", "水", "木", "金", "土"];

type Props = {
  initialEvents: CalendarEvent[];
  token: string;
};

type ModalState =
  | { open: false }
  | { open: true; mode: "create"; prefillDate: string }
  | { open: true; mode: "edit"; event: CalendarEvent };

type FormState = {
  summary: string;
  startDate: string;
  startTime: string;
  endDate: string;
  endTime: string;
  location: string;
  description: string;
};

function toISO(date: string, time: string) {
  return `${date}T${time}:00`;
}

function dateFromISO(iso: string) {
  return iso.slice(0, 10);
}

function timeFromISO(iso: string) {
  return iso.slice(11, 16);
}

function padded(n: number) {
  return String(n).padStart(2, "0");
}

function selectedDateStr(year: number, month: number, day: number) {
  return `${year}-${padded(month + 1)}-${padded(day)}`;
}

function emptyForm(prefillDate: string): FormState {
  return {
    summary: "",
    startDate: prefillDate,
    startTime: "09:00",
    endDate: prefillDate,
    endTime: "10:00",
    location: "",
    description: "",
  };
}

function formFromEvent(ev: CalendarEvent): FormState {
  return {
    summary: ev.summary,
    startDate: dateFromISO(ev.start),
    startTime: timeFromISO(ev.start),
    endDate: dateFromISO(ev.end),
    endTime: timeFromISO(ev.end),
    location: ev.location ?? "",
    description: ev.description ?? "",
  };
}

export default function CalendarView({ initialEvents, token }: Props) {
  const today = new Date();
  const [events, setEvents] = useState<CalendarEvent[]>(initialEvents);
  const [current, setCurrent] = useState(
    new Date(today.getFullYear(), today.getMonth(), 1)
  );
  const [selected, setSelected] = useState<number>(today.getDate());
  const [modal, setModal] = useState<ModalState>({ open: false });
  const [form, setForm] = useState<FormState>(emptyForm(""));
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const year = current.getFullYear();
  const month = current.getMonth();

  const firstWeekday = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells: (number | null)[] = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const eventsByDay = useMemo(() => {
    const map: Record<number, CalendarEvent[]> = {};
    for (const ev of events) {
      const d = new Date(ev.start);
      if (d.getFullYear() === year && d.getMonth() === month) {
        const day = d.getDate();
        map[day] = [...(map[day] ?? []), ev];
      }
    }
    return map;
  }, [events, year, month]);

  const selectedEvents = eventsByDay[selected] ?? [];

  const isToday = (day: number) =>
    day === today.getDate() &&
    month === today.getMonth() &&
    year === today.getFullYear();

  const prevMonth = () => setCurrent(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrent(new Date(year, month + 1, 1));

  function openCreate() {
    const prefill = selectedDateStr(year, month, selected);
    setForm(emptyForm(prefill));
    setApiError(null);
    setModal({ open: true, mode: "create", prefillDate: prefill });
  }

  function openEdit(ev: CalendarEvent) {
    setForm(formFromEvent(ev));
    setApiError(null);
    setModal({ open: true, mode: "edit", event: ev });
  }

  function closeModal() {
    setModal({ open: false });
  }

  function setField(key: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSave() {
    if (!form.summary.trim()) {
      setApiError("タイトルを入力してください");
      return;
    }
    setSaving(true);
    setApiError(null);
    const input: CalendarEventInput = {
      summary: form.summary,
      start: toISO(form.startDate, form.startTime),
      end: toISO(form.endDate, form.endTime),
      location: form.location || undefined,
      description: form.description || undefined,
    };
    try {
      if (modal.open && modal.mode === "create") {
        const created = await createCalendarEvent(token, input);
        setEvents((prev) => [...prev, created]);
      } else if (modal.open && modal.mode === "edit") {
        const updated = await updateCalendarEvent(token, modal.event.id, input);
        setEvents((prev) =>
          prev.map((ev) => (ev.id === updated.id ? updated : ev))
        );
      }
      closeModal();
    } catch (e) {
      setApiError(e instanceof Error ? e.message : "保存に失敗しました");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(eventId: string) {
    setDeleting(eventId);
    try {
      await deleteCalendarEvent(token, eventId);
      setEvents((prev) => prev.filter((ev) => ev.id !== eventId));
    } catch (e) {
      setApiError(e instanceof Error ? e.message : "削除に失敗しました");
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* 月ナビゲーション */}
      <div className="flex items-center justify-between">
        <button
          onClick={prevMonth}
          className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-500 text-lg"
        >
          ‹
        </button>
        <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
          {year}年 {month + 1}月
        </span>
        <button
          onClick={nextMonth}
          className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-500 text-lg"
        >
          ›
        </button>
      </div>

      {/* カレンダーグリッド */}
      <div className="grid grid-cols-7">
        {WEEKDAYS.map((d, i) => (
          <div
            key={d}
            className={`text-center text-xs font-medium py-2 ${
              i === 0
                ? "text-red-400"
                : i === 6
                ? "text-blue-400"
                : "text-zinc-400"
            }`}
          >
            {d}
          </div>
        ))}
        {cells.map((day, i) => {
          const colIndex = i % 7;
          const isSelected = day === selected;
          const hasEvents = day !== null && !!eventsByDay[day];
          return (
            <div
              key={i}
              onClick={() => day && setSelected(day)}
              className={`relative flex flex-col items-center py-1.5 rounded-lg transition-colors ${
                !day
                  ? "cursor-default"
                  : isSelected
                  ? "bg-zinc-800 dark:bg-zinc-200 cursor-pointer"
                  : "hover:bg-zinc-100 dark:hover:bg-zinc-700/50 cursor-pointer"
              }`}
            >
              {day && (
                <>
                  <span
                    className={`text-xs w-6 h-6 flex items-center justify-center rounded-full ${
                      isToday(day) && !isSelected
                        ? "bg-blue-500 text-white font-semibold"
                        : isSelected
                        ? "text-white dark:text-zinc-900 font-semibold"
                        : colIndex === 0
                        ? "text-red-400"
                        : colIndex === 6
                        ? "text-blue-400"
                        : "text-zinc-700 dark:text-zinc-300"
                    }`}
                  >
                    {day}
                  </span>
                  {hasEvents && (
                    <div className="flex gap-0.5 mt-0.5">
                      {eventsByDay[day].slice(0, 3).map((_, j) => (
                        <span
                          key={j}
                          className={`w-1 h-1 rounded-full ${
                            isSelected
                              ? "bg-zinc-400 dark:bg-zinc-600"
                              : "bg-blue-400"
                          }`}
                        />
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      {/* 選択日のイベント一覧 */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-widest">
            {month + 1}月{selected}日のイベント
          </h3>
          <button
            onClick={openCreate}
            className="text-xs px-3 py-1 rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-300 transition-colors"
          >
            ＋ 追加
          </button>
        </div>

        {apiError && !modal.open && (
          <p className="text-xs text-red-500 mb-2">{apiError}</p>
        )}

        {selectedEvents.length === 0 ? (
          <p className="text-sm text-zinc-400 py-6 text-center border border-dashed border-zinc-200 dark:border-zinc-700 rounded-lg">
            イベントなし
          </p>
        ) : (
          <ul className="space-y-2">
            {selectedEvents.map((ev) => (
              <li
                key={ev.id}
                className="bg-zinc-50 dark:bg-zinc-700/50 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-zinc-800 dark:text-zinc-100 truncate">
                      {ev.summary}
                    </p>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      {new Date(ev.start).toLocaleTimeString("ja-JP", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}{" "}
                      –{" "}
                      {new Date(ev.end).toLocaleTimeString("ja-JP", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                    {ev.location && (
                      <p className="text-xs text-zinc-500 mt-0.5">
                        📍 {ev.location}
                      </p>
                    )}
                    {ev.description && (
                      <p className="text-xs text-zinc-500 mt-1">
                        {ev.description}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button
                      onClick={() => openEdit(ev)}
                      className="text-xs px-2 py-1 rounded text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-600 transition-colors"
                    >
                      編集
                    </button>
                    <button
                      onClick={() => handleDelete(ev.id)}
                      disabled={deleting === ev.id}
                      className="text-xs px-2 py-1 rounded text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
                    >
                      {deleting === ev.id ? "..." : "削除"}
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* モーダル */}
      {modal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
              {modal.mode === "create" ? "イベントを追加" : "イベントを編集"}
            </h2>

            <div className="space-y-3">
              <Field label="タイトル *">
                <input
                  type="text"
                  value={form.summary}
                  onChange={(e) => setField("summary", e.target.value)}
                  placeholder="例: 会議"
                  className={inputCls}
                />
              </Field>

              <div className="grid grid-cols-2 gap-3">
                <Field label="開始日">
                  <input
                    type="date"
                    value={form.startDate}
                    onChange={(e) => setField("startDate", e.target.value)}
                    className={inputCls}
                  />
                </Field>
                <Field label="開始時刻">
                  <input
                    type="time"
                    value={form.startTime}
                    onChange={(e) => setField("startTime", e.target.value)}
                    className={inputCls}
                  />
                </Field>
                <Field label="終了日">
                  <input
                    type="date"
                    value={form.endDate}
                    onChange={(e) => setField("endDate", e.target.value)}
                    className={inputCls}
                  />
                </Field>
                <Field label="終了時刻">
                  <input
                    type="time"
                    value={form.endTime}
                    onChange={(e) => setField("endTime", e.target.value)}
                    className={inputCls}
                  />
                </Field>
              </div>

              <Field label="場所">
                <input
                  type="text"
                  value={form.location}
                  onChange={(e) => setField("location", e.target.value)}
                  placeholder="例: 東京オフィス"
                  className={inputCls}
                />
              </Field>

              <Field label="説明">
                <textarea
                  value={form.description}
                  onChange={(e) => setField("description", e.target.value)}
                  rows={3}
                  placeholder="メモや詳細など"
                  className={`${inputCls} resize-none`}
                />
              </Field>
            </div>

            {apiError && (
              <p className="text-xs text-red-500">{apiError}</p>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={closeModal}
                disabled={saving}
                className="px-4 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
              >
                キャンセル
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 text-sm rounded-lg bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-50"
              >
                {saving ? "保存中..." : "保存"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const inputCls =
  "w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-zinc-400 dark:focus:ring-zinc-500";

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs text-zinc-500 dark:text-zinc-400 mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}
