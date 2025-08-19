import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Диспетчер перевозок",
  description: "Поиск исполнителей и маршрутов"
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body className="min-h-screen">
        <div className="border-b bg-white">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-blue-600 text-2xl">✈️</div>
              <div className="text-xl font-semibold">Диспетчер перевозок</div>
            </div>
            <a href="/" className="text-sm text-blue-600 hover:underline">
              Главная
            </a>
          </div>
        </div>
        {children}
      </body>
    </html>
  );
} 