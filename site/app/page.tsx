import Image from "next/image";
import { CopyCommand } from "../components/CopyCommand";
import { LandingMotion } from "../components/LandingMotion";
import { MotionLink } from "../components/MotionLink";
import { SpecimenPoster } from "../components/SpecimenPoster";

const repository = "https://github.com/yuribodo/vox";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const steps = [
  {
    number: "01",
    name: "capture",
    description: "Hold Super + V and speak. PipeWire records a clean local audio buffer.",
    detail: "16 kHz / PCM",
  },
  {
    number: "02",
    name: "transcribe",
    description: "Whisper and Silero VAD turn the signal into words on your NVIDIA GPU.",
    detail: "large-v3-turbo / CUDA",
  },
  {
    number: "03",
    name: "insert",
    description: "Vox returns to the original field and pastes. It never presses Enter.",
    detail: "clipboard / no submit",
  },
];

export default function Home() {
  return (
    <LandingMotion>
      <a className="skip-link" href="#main">Skip to content</a>

      <header className="site-header" data-intro>
        <a className="brand" href="#top" aria-label="Vox home">
          <span className="brand-glyph" aria-hidden="true">v<span>o</span>x</span>
          <span className="brand-note">local voice interface</span>
        </a>

        <div className="header-coordinate" aria-hidden="true">
          <span>LINUX / X11</span>
          <span>40.7128°N</span>
        </div>

        <MotionLink className="header-link" href={repository}>
          source <span aria-hidden="true">↗</span>
        </MotionLink>
      </header>

      <main id="main">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero-specimen" data-specimen>
            <SpecimenPoster />
          </div>

          <div className="hero-title-wrap">
            <p className="hero-kicker" data-intro>
              <span>voice specimen 001</span>
              <span>/dev/vox</span>
            </p>
            <h1 id="hero-title" aria-label="Voice in. Text out. Nothing leaves.">
              <span data-intro>voice in.</span>
              <span data-intro>text out.</span>
              <span className="hero-title-accent" data-intro>nothing leaves.</span>
            </h1>
          </div>

          <div className="hero-detail" data-intro>
            <p>
              Push-to-talk dictation for Linux. Audio becomes text on your
              machine, then lands exactly where your cursor was.
            </p>
            <div className="hero-actions">
              <MotionLink className="action action-primary" href="#install">
                install vox <span aria-hidden="true">↓</span>
              </MotionLink>
              <MotionLink className="action action-quiet" href={repository}>
                inspect the source <span aria-hidden="true">↗</span>
              </MotionLink>
            </div>
          </div>

          <div className="hero-calibration" aria-hidden="true" data-intro>
            <span>REC</span>
            <i />
            <span>00:06.4</span>
          </div>
        </section>

        <section className="story" id="signal" aria-labelledby="story-title">
          <header className="story-heading" data-reveal>
            <p className="section-label"><span>01</span> the signal</p>
            <h2 id="story-title">the whole trip<br />stays on this desk.</h2>
            <p>
              Vox keeps the path short: microphone, local model, cursor. No
              account, no upload, no hidden handoff.
            </p>
          </header>

          <figure className="editorial-specimen story-specimen" data-section-image>
            <div className="specimen-image" data-image-inner>
              <Image
                alt="Microphone diaphragm connected to a printed waveform, signal board and two blank transcript slips"
                src={`${basePath}/images/signal-specimen.webp`}
                fill
                sizes="(max-width: 720px) 100vw, 94vw"
              />
            </div>
            <figcaption>
              <span>FIG. V—002</span>
              <span>signal / decode / return</span>
            </figcaption>
          </figure>

          <ol className="story-steps" data-step-list id="signal-steps">
            {steps.map((step) => (
              <li key={step.name}>
                <div className="step-heading">
                  <span>{step.number}</span>
                  <h3>{step.name}</h3>
                </div>
                <p>{step.description}</p>
                <code>{step.detail}</code>
              </li>
            ))}
          </ol>
        </section>

        <section className="build" id="install" aria-labelledby="build-title">
          <header className="build-heading" data-reveal>
            <p className="section-label"><span>02</span> your machine</p>
            <h2 id="build-title">you own<br />the listener.</h2>
            <p>
              Vox is open source and runs where you work: Cinnamon on X11,
              PipeWire, Whisper and NVIDIA CUDA.
            </p>
          </header>

          <figure className="editorial-specimen build-specimen" data-section-image>
            <div className="specimen-image" data-image-inner>
              <Image
                alt="Mechanical keys, aluminum heatsink, circuit board, USB cable and precision tools arranged as a Linux workstation specimen"
                src={`${basePath}/images/machine-specimen.webp`}
                fill
                sizes="(max-width: 720px) 100vw, 94vw"
              />
            </div>
            <figcaption>
              <span>FIG. V—003</span>
              <span>workstation kit / local compute</span>
            </figcaption>
          </figure>

          <div className="install-sheet" data-reveal>
            <div className="install-sheet-title">
              <span>quick start</span>
              <span>2 commands</span>
            </div>

            <div className="command-row">
              <span className="command-index">01</span>
              <code>git clone https://github.com/yuribodo/vox.git &amp;&amp; cd vox</code>
              <CopyCommand command="git clone https://github.com/yuribodo/vox.git && cd vox" />
            </div>
            <div className="command-row">
              <span className="command-index">02</span>
              <code>make build &amp;&amp; make fetch-whisper &amp;&amp; make doctor</code>
              <CopyCommand command="make build && make fetch-whisper && make doctor" />
            </div>

            <div className="requirements">
              <span>Cinnamon / X11</span><span>PipeWire</span><span>NVIDIA CUDA</span><span>Go 1.26</span>
            </div>
          </div>

          <footer className="build-footer" data-reveal>
            <MotionLink className="action action-primary" href={`${repository}#install-and-start-using-vox`}>
              read the install guide <span aria-hidden="true">↗</span>
            </MotionLink>
            <div className="footer-meta">
              <span>MIT / open source</span>
              <a href="third-party-licenses.txt">third-party licenses</a>
              <span>© 2026 contributors</span>
            </div>
          </footer>
        </section>
      </main>
    </LandingMotion>
  );
}
