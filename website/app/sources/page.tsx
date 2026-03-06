import Link from "next/link";
import Image from "next/image";

const sources = [
  {
    category: "Computer Vision & AI",
    items: [
      {
        name: "MediaPipe Face Landmarker",
        author: "Google",
        url: "https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker",
        desc: "Real-time face landmark detection with 478 points and facial blendshape scores. Powers head pose estimation and blink/mouth detection.",
        license: "Apache 2.0",
      },
      {
        name: "MediaPipe Gesture Recognizer",
        author: "Google",
        url: "https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer",
        desc: "Pre-trained hand gesture recognition model detecting thumbs up, peace sign, fist, open palm, and more.",
        license: "Apache 2.0",
      },
      {
        name: "OpenCV (cv2)",
        author: "OpenCV Team",
        url: "https://opencv.org",
        desc: "Open source computer vision library used for webcam capture, frame processing, and image manipulation.",
        license: "Apache 2.0",
      },
      {
        name: "MediaPipe Python Tasks API",
        author: "Google",
        url: "https://ai.google.dev/edge/mediapipe/solutions/guide",
        desc: "The Task API used to run FaceLandmarker and GestureRecognizer in VIDEO mode for real-time processing.",
        license: "Apache 2.0",
      },
    ],
  },
  {
    category: "Application Framework",
    items: [
      {
        name: "PyQt6",
        author: "Riverbank Computing",
        url: "https://www.riverbankcomputing.com/software/pyqt/",
        desc: "Python bindings for the Qt6 application framework. Used to build the desktop GUI, camera preview widget, and system tray integration.",
        license: "GPL v3",
      },
      {
        name: "Qt6",
        author: "The Qt Company",
        url: "https://www.qt.io",
        desc: "Cross-platform application and UI framework underlying PyQt6.",
        license: "LGPL v3",
      },
      {
        name: "Python",
        author: "Python Software Foundation",
        url: "https://www.python.org",
        desc: "Primary programming language. Python 3.11+ used for all application logic, threading, and data processing.",
        license: "PSF License",
      },
    ],
  },
  {
    category: "Input Control",
    items: [
      {
        name: "pynput",
        author: "Moses Palmér",
        url: "https://pynput.readthedocs.io",
        desc: "Cross-platform library for controlling and monitoring keyboard and mouse input. Used to emit real keypresses and mouse events to any macOS application.",
        license: "LGPL v3",
      },
    ],
  },
  {
    category: "Web & Distribution",
    items: [
      {
        name: "Next.js 15",
        author: "Vercel",
        url: "https://nextjs.org",
        desc: "React framework used to build this website with App Router, server components, and static export.",
        license: "MIT",
      },
      {
        name: "Tailwind CSS",
        author: "Tailwind Labs",
        url: "https://tailwindcss.com",
        desc: "Utility-first CSS framework used to style this website.",
        license: "MIT",
      },
      {
        name: "Vercel",
        author: "Vercel Inc.",
        url: "https://vercel.com",
        desc: "Hosting and deployment platform for this website.",
        license: "Commercial (free tier)",
      },
      {
        name: "PyInstaller",
        author: "PyInstaller Team",
        url: "https://pyinstaller.org",
        desc: "Used to bundle the Python application and all its dependencies into a standalone macOS .app bundle.",
        license: "GPL v2 with exception",
      },
    ],
  },
  {
    category: "Research & Inspiration",
    items: [
      {
        name: "Switch Access for Android",
        author: "Google",
        url: "https://support.google.com/accessibility/android/answer/6122836",
        desc: "Google's switch access accessibility feature — inspiration for the configurable switch model in OpenCV.",
        license: "—",
      },
      {
        name: "Eye Aspect Ratio (EAR) for Blink Detection",
        author: "Soukupová & Čech, 2016",
        url: "https://vision.fe.uni-lj.si/cvww2016/proceedings/papers/05.pdf",
        desc: "Academic paper describing the Eye Aspect Ratio technique for detecting eye blinks from facial landmarks.",
        license: "Academic",
      },
      {
        name: "Web Content Accessibility Guidelines (WCAG) 2.1",
        author: "W3C",
        url: "https://www.w3.org/TR/WCAG21/",
        desc: "W3C standard for web accessibility. Referenced for understanding input modality requirements.",
        license: "W3C Document License",
      },
      {
        name: "Apple Accessibility — Switch Control",
        author: "Apple",
        url: "https://support.apple.com/guide/iphone/switch-control-settings-iphe609e3438/ios",
        desc: "Apple's built-in Switch Control feature for macOS/iOS — inspiration for the system-wide adaptive controller approach.",
        license: "—",
      },
    ],
  },
];

export default function SourcesPage() {
  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="fixed top-0 inset-x-0 z-50 glass border-b border-white/[0.06]">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/logo.png" alt="OpenCV" width={28} height={28} className="rounded-lg" />
            <span className="font-bold text-white tracking-tight">OpenCV</span>
          </Link>
          <Link href="/" className="text-sm text-white/50 hover:text-white transition-colors">
            ← Back
          </Link>
        </div>
      </nav>

      <div className="pt-28 pb-24 px-6 max-w-4xl mx-auto">
        <div className="mb-12">
          <span className="text-teal text-sm font-semibold tracking-widest uppercase">Attribution</span>
          <h1 className="text-4xl font-black text-white mt-3 mb-4">Sources & Credits</h1>
          <p className="text-white/50 text-lg leading-relaxed">
            OpenCV is built on the shoulders of incredible open-source projects.
            Below are all the libraries, tools, and research that made it possible.
          </p>
        </div>

        <div className="space-y-12">
          {sources.map((group) => (
            <div key={group.category}>
              <h2 className="text-xs font-bold tracking-widest uppercase text-brand-light mb-4 border-b border-white/[0.06] pb-3">
                {group.category}
              </h2>
              <div className="space-y-3">
                {group.items.map((item) => (
                  <a key={item.name} href={item.url} target="_blank" rel="noopener noreferrer"
                     className="block glass rounded-2xl p-5 hover:bg-white/[0.07] transition-colors group">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <span className="text-white font-semibold group-hover:text-brand-light transition-colors">
                            {item.name}
                          </span>
                          <span className="text-white/30 text-sm">by {item.author}</span>
                        </div>
                        <p className="text-white/50 text-sm leading-relaxed">{item.desc}</p>
                      </div>
                      <div className="shrink-0 text-right">
                        <span className="inline-block px-2 py-0.5 rounded text-xs bg-white/5 text-white/30 font-mono">
                          {item.license}
                        </span>
                        <div className="text-white/20 text-xs mt-1 group-hover:text-brand-light/60 transition-colors">↗</div>
                      </div>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-16 glass rounded-3xl p-8 text-center">
          <p className="text-white/40 text-sm leading-relaxed">
            OpenCV was created by <strong className="text-white">Jacob Majors</strong> for
            {" "}<strong className="text-white">Ramsey Mussalum&apos;s</strong> Design for Social Good class
            at <strong className="text-white">Sonoma Academy</strong>, March 2026.
            <br className="hidden md:block" />
            {" "}All source code is available on{" "}
            <a href="https://github.com/jacob-majors/open-CV"
               className="text-brand-light hover:underline" target="_blank" rel="noopener noreferrer">
              GitHub
            </a>.
          </p>
        </div>
      </div>
    </main>
  );
}
