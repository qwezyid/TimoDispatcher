import "./globals.css";
import React from "react";

export const metadata = {
  title: "Диспетчер перевозок",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="bg-gray-50">
        <header className="border-b bg-white">
          <div className="max-w-7xl mx-auto px-6 py-4 text-xl font-semibold">🧭 Диспетчер перевозок</div>
        </header>
        {children}
      </body>
    </html>
  );
}
