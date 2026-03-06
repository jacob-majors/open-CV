import Image from "next/image";
import Link from "next/link";

const DOWNLOAD_URL =
  "https://github.com/jacob-majors/open-CV/releases/latest/download/OpenCV.app.zip";
const GITHUB_URL = "https://github.com/jacob-majors/open-CV";
const ISSUES_URL = "https://github.com/jacob-majors/open-CV/issues/new";

const features = [
  { icon: "👁", title: "Eye Blinks", desc: "Blink left, right, or both eyes to trigger any key. Precise threshold control." },
  { icon: "↕", title: "Head Movement", desc: "Turn, tilt, and roll your head in 6 directions. Works with any degree of motion." },
  { icon: "😮", title: "Mouth & Brows", desc: "Open your mouth, raise eyebrows, or smile — each maps to a separate action." },
  { icon: "👍", title: "Hand Gestures", desc: "Thumbs up, peace sign, fist, open palm and more. No gloves or hardware needed." },
  { icon: "✋", title: "Hand Position", desc: "Move your hand left, right, up or down in frame to trigger directional controls." },
  { icon: "⌨️", title: "Full Keyboard", desc: "Tap, hold, or combo any key — space, arrows, WASD, F-keys, Cmd+anything." },
];

const howItWorks = [
  { step: "1", title: "Download & open", desc: "Download OpenCV.app, double-click, allow camera access." },
  { step: "2", title: "Grant accessibility", desc: "Allow Accessibility in System Settings so keypresses reach other apps." },
  { step: "3", title: "Configure switches", desc: "Map any movement to any key. Set threshold and cooldown per switch." },
  { step: "4", title: "Start tracking", desc: "Hit Start or press ⌘⇧O from anywhere — even while a game is running." },
];

export default function Home() {
  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="fixed top-0 inset-x-0 z-50 glass border-b border-white/[0.06]">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image src="/logo.png" alt="OpenCV" width={32} height={32} className="rounded-lg" />
            <span className="font-bold text-white tracking-tight">OpenCV</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-white/60">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#story" className="hover:text-white transition-colors">Story</a>
            <Link href="/sources" className="hover:text-white transition-colors">Sources</Link>
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer"
               className="hover:text-white transition-colors">GitHub</a>
            <a href={DOWNLOAD_URL}
               className="px-4 py-1.5 rounded-full bg-brand text-white text-xs font-semibold hover:bg-brand-light transition-colors">
              Download
            </a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-24 px-6 text-center relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-brand/10 blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] rounded-full bg-teal/5 blur-2xl" />
        </div>

        <div className="relative max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-sm text-white/60 mb-8">
            <span className="w-2 h-2 rounded-full bg-teal animate-pulse" />
            Free & open source · macOS · No hardware required
          </div>

          <div className="flex justify-center mb-8">
            <Image src="/logo.png" alt="OpenCV" width={120} height={120}
                   className="rounded-3xl glow" />
          </div>

          <h1 className="text-5xl md:text-7xl font-black tracking-tight text-white mb-6 leading-tight">
            Control your Mac<br />
            <span className="gradient-text">with your face.</span>
          </h1>

          <p className="text-xl text-white/50 max-w-2xl mx-auto mb-10 leading-relaxed">
            OpenCV uses your webcam to detect facial movements, head rotations, and hand gestures —
            then turns them into real keypresses. Control any game, app, or tool hands-free.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4">
            <a href={DOWNLOAD_URL}
               className="flex items-center gap-3 px-8 py-4 rounded-2xl bg-brand hover:bg-brand-light transition-all text-white font-bold text-lg glow">
              <span>↓</span>
              Download for macOS
              <span className="text-white/50 font-normal text-sm">Free</span>
            </a>
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer"
               className="flex items-center gap-2 px-8 py-4 rounded-2xl glass hover:bg-white/10 transition-all text-white font-semibold text-lg">
              View on GitHub →
            </a>
          </div>

          <p className="mt-6 text-sm text-white/30">
            macOS 12+ · Requires camera & Accessibility permission
          </p>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-black text-white mb-4">Every movement is a button.</h2>
            <p className="text-white/50 text-lg max-w-xl mx-auto">
              Map any facial movement or hand gesture to any key — with adjustable sensitivity and cooldown.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f) => (
              <div key={f.title} className="glass rounded-2xl p-6 hover:bg-white/[0.07] transition-colors group">
                <div className="text-4xl mb-4">{f.icon}</div>
                <h3 className="text-white font-bold text-lg mb-2">{f.title}</h3>
                <p className="text-white/50 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 px-6 border-t border-white/[0.06]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-black text-white mb-4">Up and running in minutes.</h2>
          </div>
          <div className="grid md:grid-cols-4 gap-6">
            {howItWorks.map((s) => (
              <div key={s.step} className="text-center">
                <div className="w-12 h-12 rounded-2xl bg-brand/20 border border-brand/30 flex items-center justify-center text-brand-light font-black text-xl mx-auto mb-4">
                  {s.step}
                </div>
                <h3 className="text-white font-bold mb-2">{s.title}</h3>
                <p className="text-white/40 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Story */}
      <section id="story" className="py-24 px-6 border-t border-white/[0.06]">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <span className="text-teal text-sm font-semibold tracking-widest uppercase">The Story</span>
            <h2 className="text-4xl font-black text-white mt-3">Built for people who need it most.</h2>
          </div>

          <div className="glass rounded-3xl p-8 md:p-12 space-y-6 text-white/70 leading-relaxed text-lg">
            <p>
              OpenCV started in a classroom at <strong className="text-white">Sonoma Academy</strong>, in
              {" "}<strong className="text-white">Ramsey Mussalum&apos;s Design for Social Good</strong> course —
              a class built around one idea: design should solve real problems for real people.
            </p>
            <p>
              The assignment was to create something that made a meaningful difference. The question became:
              what do people with limited motor ability use to interact with technology? Expensive,
              proprietary hardware. Complex setups. Devices that cost thousands of dollars.
            </p>
            <p>
              OpenCV is the answer: a free, open-source adaptive controller that works with just a webcam.
              No special hardware. No subscriptions. Just your face and your Mac.
            </p>
            <p>
              Whether you have a condition that limits hand mobility, are recovering from an injury,
              or simply want a new way to interact with your computer — OpenCV turns the camera
              you already have into a full input device.
            </p>
            <div className="pt-4 border-t border-white/10">
              <p className="text-white/40 text-base">
                Made by <strong className="text-white">Jacob Majors</strong> ·
                Sonoma Academy · March 2026
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Download CTA */}
      <section className="py-24 px-6 border-t border-white/[0.06]">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-4xl font-black text-white mb-4">Ready to try it?</h2>
          <p className="text-white/50 text-lg mb-10">
            Free, open source, and always will be.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <a href={DOWNLOAD_URL}
               className="flex items-center gap-3 px-8 py-4 rounded-2xl bg-brand hover:bg-brand-light transition-all text-white font-bold text-lg glow">
              ↓ Download OpenCV.app
            </a>
            <a href={ISSUES_URL} target="_blank" rel="noopener noreferrer"
               className="flex items-center gap-2 px-8 py-4 rounded-2xl glass hover:bg-white/10 transition-all text-white font-semibold text-lg">
              Report an Issue
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/[0.06] py-10 px-6">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-4 text-sm text-white/30">
          <div className="flex items-center gap-3">
            <Image src="/logo.png" alt="" width={20} height={20} className="rounded opacity-60" />
            <span>OpenCV — Adaptive Vision Controller</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/sources" className="hover:text-white/60 transition-colors">Sources</Link>
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer"
               className="hover:text-white/60 transition-colors">GitHub</a>
            <a href={ISSUES_URL} target="_blank" rel="noopener noreferrer"
               className="hover:text-white/60 transition-colors">Report Issue</a>
          </div>
          <span>Made by Jacob Majors · Sonoma Academy · 2026</span>
        </div>
      </footer>
    </main>
  );
}
