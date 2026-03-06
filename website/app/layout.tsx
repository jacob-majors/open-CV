import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpenCV — Adaptive Vision Controller",
  description:
    "Control your Mac with your face, head movements, and hand gestures. Built for accessibility by Jacob Majors at Sonoma Academy.",
  openGraph: {
    title: "OpenCV — Adaptive Vision Controller",
    description: "Control any app or game with your face and hands.",
    images: ["/logo.png"],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
