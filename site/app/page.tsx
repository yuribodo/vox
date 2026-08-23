import { CopyCommand } from "../components/CopyCommand";
import { LandingMotion } from "../components/LandingMotion";
import { MotionLink } from "../components/MotionLink";

const repository = "https://github.com/yuribodo/vox";
const cloneCommand = "git clone https://github.com/yuribodo/vox.git && cd vox";
const buildCommand = "make build && make fetch-whisper && make doctor";

const details = [
  {
    title: "Capture stays local",
    description: "PipeWire records directly on your machine. There is no upload step.",
    meta: "16 kHz / PCM",
  },
  {
    title: "Your GPU does the work",
    description: "Whisper and Silero VAD transcribe without an account or API key.",
    meta: "CUDA / local model",
  },
  {
    title: "Text returns to the cursor",
    description: "Release the shortcut and Vox pastes where you started. It never presses Enter.",
    meta: "clipboard / no submit",
  },
];

export default function Home() {
  return (
    <LandingMotion>
      <a className="skip-link" href="#main">Skip to content</a>

      <header className="site-header" data-header>
        <a className="brand" href="#top" aria-label="Vox home">
          <span aria-hidden="true" /> vox
        </a>
        <nav aria-label="Main navigation">
          <a href="#how">How it works</a>
          <a href="#install">Install</a>
          <MotionLink href={repository}>GitHub ↗</MotionLink>
        </nav>
      </header>

      <main id="main">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow" data-hero-fade>Open source · built for Linux</p>
            <h1 id="hero-title">
              <span className="hero-line"><span data-hero-line>Dictate anywhere.</span></span>
              <span className="hero-line hero-line-muted"><span data-hero-line>Keep it local.</span></span>
            </h1>
            <p className="hero-description" data-hero-fade>
              Hold <kbd>Super + V</kbd>, speak, and release. Vox turns your voice
              into text on your machine, then returns it to your cursor.
            </p>
            <div className="hero-actions" data-hero-fade>
              <MotionLink className="button button-primary" href="#install">
                Install Vox
              </MotionLink>
              <MotionLink className="button button-secondary" href={repository}>
                View source <span aria-hidden="true">↗</span>
              </MotionLink>
            </div>
          </div>

          <div className="signal" data-signal aria-label="Voice is captured, transcribed locally, and returned as text">
            <div className="signal-meta">
              <span><i aria-hidden="true" /><span data-signal-status>ready / local</span></span>
              <code>SUPER + V</code>
            </div>
            <div className="signal-stage">
              <svg viewBox="0 0 1000 180" role="img" aria-label="A waveform enters a local processor and resolves into transcript lines">
                <g className="signal-grid" aria-hidden="true">
                  <path d="M1 45H999M1 90H999M1 135H999" />
                  <path d="M125 1V179M250 1V179M375 1V179M625 1V179M750 1V179M875 1V179" />
                </g>
                <path
                  className="signal-wave"
                  data-signal-path
                  d="M1 90H52c10 0 13-18 24-18s13 40 25 40 14-70 28-70 15 102 31 102 16-117 33-117 18 126 36 126 17-108 34-108s17 80 34 80 18-52 35-52 18 31 35 31 17-17 34-17 18 8 35 8h61"
                />
                <path className="processor-link" d="M477 90H536" />
                <g className="processor" data-processor>
                  <circle className="processor-ring" cx="566" cy="90" r="28" />
                  <circle className="processor-core" cx="566" cy="90" r="5" />
                  <path d="M566 62V48M566 132V118M538 90H524M608 90H594" />
                </g>
                <g className="transcript-lines" data-transcript-lines>
                  <path d="M625 58H950" />
                  <path d="M625 80H875" />
                  <path d="M625 102H924" />
                  <path d="M625 124H790" />
                </g>
              </svg>
              <div className="signal-labels" aria-hidden="true">
                <span>voice / PipeWire</span>
                <span>local decode</span>
                <span>text / cursor</span>
              </div>
            </div>
            <div className="signal-output" data-signal-result>
              <span>output</span>
              <p>Voice becomes text right here.<i aria-hidden="true" /></p>
            </div>
          </div>
        </section>

        <section className="how" id="how" aria-labelledby="how-title">
          <div className="section-heading" data-reveal>
            <p className="section-label">How it works</p>
            <h2 id="how-title">Private by architecture,<br />not by policy.</h2>
            <p>
              Vox has a deliberately short path from microphone to text. Every
              part of that path is visible and runs locally.
            </p>
          </div>

          <ol className="detail-list">
            {details.map((detail, index) => (
              <li key={detail.title} data-detail>
                <span className="detail-number">0{index + 1}</span>
                <div>
                  <h3>{detail.title}</h3>
                  <p>{detail.description}</p>
                </div>
                <code>{detail.meta}</code>
              </li>
            ))}
          </ol>
        </section>

        <section className="install" id="install" aria-labelledby="install-title">
          <div className="install-copy" data-reveal>
            <p className="section-label">Get started</p>
            <h2 id="install-title">Two commands.<br />Then talk.</h2>
            <p>
              Vox targets Cinnamon on X11 with PipeWire and NVIDIA CUDA. The
              doctor command checks your machine before you begin.
            </p>
          </div>

          <div className="commands">
            <div className="command-row">
              <span>1</span>
              <code>{cloneCommand}</code>
              <CopyCommand command={cloneCommand} />
            </div>
            <div className="command-row">
              <span>2</span>
              <code>{buildCommand}</code>
              <CopyCommand command={buildCommand} />
            </div>
          </div>

          <div className="install-footer" data-reveal>
            <ul aria-label="Requirements">
              <li>Cinnamon / X11</li>
              <li>PipeWire</li>
              <li>NVIDIA CUDA</li>
              <li>Go 1.26</li>
            </ul>
            <MotionLink href={`${repository}#install-and-start-using-vox`}>
              Read the full installation guide <span aria-hidden="true">↗</span>
            </MotionLink>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <span>Vox · MIT License</span>
        <a href="third-party-licenses.txt">Third-party licenses</a>
        <a href={repository}>Source on GitHub ↗</a>
      </footer>
    </LandingMotion>
  );
}
