import Image from "next/image";
import { CopyCommand } from "../components/CopyCommand";
import { LandingMotion } from "../components/LandingMotion";
import { MotionLink } from "../components/MotionLink";

const repository = "https://github.com/yuribodo/vox";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const cloneCommand = "git clone https://github.com/yuribodo/vox.git && cd vox";
const buildCommand = "make build && make fetch-whisper && make doctor";

const flow = [
  {
    number: "01",
    verb: "hold",
    shortcut: "SUPER + V",
    copy: "Vox starts a clean 16 kHz recording through PipeWire.",
  },
  {
    number: "02",
    verb: "speak",
    shortcut: "LOCAL CUDA",
    copy: "Whisper and Silero VAD decode speech on your own GPU.",
  },
  {
    number: "03",
    verb: "release",
    shortcut: "CURSOR ← TEXT",
    copy: "The transcript returns to the field you left. Vox never submits it.",
  },
];

export default function Home() {
  return (
    <LandingMotion>
      <a className="skip-link" href="#main">Skip to content</a>

      <header className="site-header" data-intro>
        <a className="brand" href="#top" aria-label="Vox home">vox<span>/</span></a>
        <p className="header-status"><i aria-hidden="true" /> open source · local only</p>
        <MotionLink className="header-link" href={repository}>
          GitHub <span aria-hidden="true">↗</span>
        </MotionLink>
      </header>

      <main id="main">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero-media" data-hero-media>
            <Image
              alt="A machined acoustic diaphragm turning a pressure wave into precise horizontal signal lines"
              src={`${basePath}/images/resonance.webp`}
              fill
              priority
              sizes="100vw"
            />
            <div className="hero-shade" />
          </div>

          <div className="hero-copy">
            <p className="eyebrow" data-hero-copy>
              <span>push-to-talk for Linux</span>
              <span>v0.1 / X11</span>
            </p>
            <h1 id="hero-title" data-hero-copy>
              <span>Speak anywhere.</span>
              <span className="hero-accent">Send nowhere.</span>
            </h1>
            <div className="hero-summary" data-hero-copy>
              <p>
                Hold <kbd>Super + V</kbd>, talk, release. Vox transcribes on your
                machine and puts the words back at your cursor.
              </p>
              <div className="hero-actions">
                <MotionLink className="button button-solid" href="#install">
                  Get Vox <span aria-hidden="true">↓</span>
                </MotionLink>
                <MotionLink className="button button-ghost" href={repository}>
                  Read the source <span aria-hidden="true">↗</span>
                </MotionLink>
              </div>
            </div>
          </div>

          <div className="hero-readout" data-hero-copy aria-hidden="true">
            <span>INPUT / 16 KHZ</span>
            <span className="readout-line"><i /></span>
            <span>DEVICE / YOURS</span>
          </div>
        </section>

        <section className="protocol" id="how" aria-labelledby="protocol-title">
          <header className="protocol-header" data-reveal>
            <p className="section-index">01 / THE LOCAL LOOP</p>
            <h2 id="protocol-title">Three moves.<br />Zero network.</h2>
            <p className="protocol-intro">
              A short path from microphone to cursor. Every stage happens on the
              machine already in front of you.
            </p>
          </header>

          <ol className="flow" data-flow>
            {flow.map((item) => (
              <li key={item.verb} data-flow-row>
                <span className="flow-number">{item.number}</span>
                <h3>{item.verb}</h3>
                <div className="flow-detail">
                  <code>{item.shortcut}</code>
                  <p>{item.copy}</p>
                </div>
                <span className="flow-rule" aria-hidden="true"><i /></span>
              </li>
            ))}
          </ol>

          <p className="protocol-statement" data-reveal>
            No account. No upload.<br /><span>No accidental send.</span>
          </p>
        </section>

        <section className="install" id="install" aria-labelledby="install-title">
          <div className="install-top" data-reveal>
            <p className="section-index">02 / BUILD IT</p>
            <h2 id="install-title">Your machine.<br />Your listener.</h2>
            <p>
              Vox is MIT-licensed. Inspect every line, change the hotkey, swap
              the model, or keep it exactly as it is.
            </p>
          </div>

          <div className="command-list" data-reveal>
            <div className="command-line">
              <span>01</span>
              <code>{cloneCommand}</code>
              <CopyCommand command={cloneCommand} />
            </div>
            <div className="command-line">
              <span>02</span>
              <code>{buildCommand}</code>
              <CopyCommand command={buildCommand} />
            </div>
          </div>

          <div className="install-bottom" data-reveal>
            <ul aria-label="Requirements">
              <li>Cinnamon / X11</li>
              <li>PipeWire</li>
              <li>NVIDIA CUDA</li>
              <li>Go 1.26</li>
            </ul>
            <MotionLink className="install-link" href={`${repository}#install-and-start-using-vox`}>
              Full installation guide <span aria-hidden="true">↗</span>
            </MotionLink>
          </div>

          <footer className="site-footer">
            <span>VOX / 2026</span>
            <span>MIT OPEN SOURCE</span>
            <a href="third-party-licenses.txt">LICENSES ↗</a>
          </footer>
        </section>
      </main>
    </LandingMotion>
  );
}
