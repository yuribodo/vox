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

      <header className="site-header" data-intro>
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
            <p className="eyebrow" data-intro>Open source · built for Linux</p>
            <h1 id="hero-title" data-intro>
              Dictate anywhere.<br /><span>Keep it local.</span>
            </h1>
            <p className="hero-description" data-intro>
              Hold <kbd>Super + V</kbd>, speak, and release. Vox turns your voice
              into text on your machine, then returns it to your cursor.
            </p>
            <div className="hero-actions" data-intro>
              <MotionLink className="button button-primary" href="#install">
                Install Vox
              </MotionLink>
              <MotionLink className="button button-secondary" href={repository}>
                View source <span aria-hidden="true">↗</span>
              </MotionLink>
            </div>
          </div>

          <div className="signal" data-signal aria-label="Voice becomes text locally">
            <div className="signal-meta">
              <span><i aria-hidden="true" /> listening</span>
              <code>SUPER + V</code>
            </div>
            <svg viewBox="0 0 1000 116" role="img" aria-label="A voice waveform resolving into a straight text line">
              <path className="signal-guide" d="M1 58H999" />
              <path
                className="signal-wave"
                data-signal-path
                d="M1 58H92c14 0 17-22 31-22s19 52 34 52 17-71 34-71 20 90 38 90 19-79 37-79 20 59 38 59 18-42 35-42s20 28 38 28 19-17 36-17 19 9 37 9h120c16 0 23-7 39-7h424"
              />
              <circle data-signal-dot cx="508" cy="58" r="5" />
            </svg>
            <div className="signal-output">
              <span>release</span>
              <p>Voice becomes text right here.</p>
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

          <div className="commands" data-reveal>
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
