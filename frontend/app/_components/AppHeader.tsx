"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

type Props = {
  actions?: React.ReactNode;
};

export default function AppHeader({ actions }: Props) {
  const pathname = usePathname();

  const navItem = (href: string, label: string) => {
    const isActive = pathname === href;
    return (
      <Link
        href={href}
        className={`text-sm px-3 py-1.5 rounded-md transition-colors ${
          isActive
            ? "bg-zinc-100 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 font-medium"
            : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <header className="bg-white dark:bg-zinc-800 border-b border-zinc-200 dark:border-zinc-700 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
          MailAI
        </h1>
        <nav className="flex gap-1">
          {navItem("/", "ダッシュボード")}
          {navItem("/todos", "課題")}
          {navItem("/calendar", "カレンダー")}
          {navItem("/settings", "設定")}
        </nav>
        <Link
          href="/mails/compose"
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
            <path d="M1.5 8.67v8.58a3 3 0 0 0 3 3h15a3 3 0 0 0 3-3V8.67l-8.928 5.493a3 3 0 0 1-3.144 0L1.5 8.67Z" />
            <path d="M22.5 6.908V6.75a3 3 0 0 0-3-3h-15a3 3 0 0 0-3 3v.158l9.714 5.978a1.5 1.5 0 0 0 1.572 0L22.5 6.908Z" />
          </svg>
          新規作成
        </Link>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}
