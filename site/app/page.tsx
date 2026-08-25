import { CopyCommand } from "../components/CopyCommand";
import { LandingMotion } from "../components/LandingMotion";
import { MotionLink } from "../components/MotionLink";
import { VoicePresence } from "../components/VoicePresence";

const repository = "https://github.com/yuribodo/vox";
const cloneCommand = "git clone https://github.com/yuribodo/vox.git && cd vox";
const buildCommand = "make build && make fetch-whisper && make doctor";

const details = [
  {
    title: "Listen",
    description: "PipeWire captures your voice directly from the active microphone.",
    meta: "PipeWire · 16 kHz",
  },
  {
    title: "Transcribe",
    description: "Whisper and Silero VAD run on your GPU—no API key, no round trip.",
    meta: "Whisper · CUDA",
  },
  {
    title: "Return",
    description: "The transcript lands at your cursor. Vox pastes the words, never Enter.",
    meta: "Clipboard · no submit",
  },
];

const transcript = ["Voice", "becomes", "text", "exactly", "where", "you", "need", "it."];

const privacy = ["No account", "No API key", "No remote retention"];

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

          <VoicePresence words={transcript} />
        </section>

        <section className="how" id="how" aria-labelledby="how-title">
          <div className="section-heading" data-reveal>
            <p className="section-label">How it works</p>
            <h2 id="how-title">A local loop.</h2>
            <p>
              From microphone to cursor without a server in between. The whole
              path runs on hardware you control.
            </p>
          </div>

          <div className="loop-group">
            <ol className="loop" data-loop>
              {details.map((detail, index) => (
                <li key={detail.title}>
                  <span>0{index + 1}</span>
                  <h3>{detail.title}</h3>
                  <p>{detail.description}</p>
                  <code>{detail.meta}</code>
                </li>
              ))}
            </ol>
            <div className="privacy-bar" data-reveal>
              <p>
                <strong>0 B</strong>
                uploaded
              </p>
              <ul aria-label="Privacy guarantees">
                {privacy.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          </div>
        </section>

        <section className="install" id="install" aria-labelledby="install-title">
          <div className="install-copy" data-reveal>
            <p className="section-label">Get started</p>
            <h2 id="install-title">Ready in two commands.</h2>
            <p>
              Clone, build, and let the doctor check your setup. Your voice
              never needs an account to get started.
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
