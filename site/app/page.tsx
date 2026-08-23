import { CopyCommand } from "../components/CopyCommand";
import { LandingMotion } from "../components/LandingMotion";
import { MotionLink } from "../components/MotionLink";
import { SpecimenPoster } from "../components/SpecimenPoster";

const repository = "https://github.com/yuribodo/vox";

const processSteps = [
  {
    number: "01",
    label: "capture",
    title: "Hold. Speak. Release.",
    body: "Vox records a clean mono stream through PipeWire while the Flow Bar gives you just enough feedback.",
    meta: "16 kHz / PCM / local buffer",
  },
  {
    number: "02",
    label: "decode",
    title: "Your GPU does the listening.",
    body: "Whisper and Silero VAD turn the signal into words on the workstation. No transcription round trip.",
    meta: "large-v3-turbo / CUDA",
  },
  {
    number: "03",
    label: "insert",
    title: "Text returns to the cursor.",
    body: "Vox restores focus and pastes the transcript where you started. It never submits on your behalf.",
    meta: "clipboard / no automatic Enter",
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

        <section className="process" id="signal" aria-labelledby="process-title">
          <header className="process-heading" data-reveal>
            <p className="section-label"><span>01</span> signal path</p>
            <h2 id="process-title">the shortest route<br />from voice to text.</h2>
            <p className="process-intro">
              One gesture in. One paste out. The signal never needs to become
              somebody else&apos;s data.
            </p>
          </header>

          <div className="process-body">
            <div className="signal-stage" aria-hidden="true">
              <div className="signal-ruler"><span>0</span><span>20</span><span>40</span><span>60</span><span>80</span><span>100</span></div>
              <div className="signal-viewport">
                <div className="signal-beam" data-signal-beam />

                <div className="signal-frame is-active" data-signal-frame>
                  <p className="signal-state">input / armed</p>
                  <svg className="voice-trace" viewBox="0 0 900 240" preserveAspectRatio="none">
                    <path
                      data-voice-path
                      d="M0 122 L32 122 L48 118 L65 128 L82 116 L99 130 L116 92 L132 158 L149 70 L166 176 L183 109 L200 134 L216 82 L233 164 L250 102 L267 138 L284 47 L300 197 L317 86 L334 155 L351 108 L368 132 L385 98 L401 145 L418 113 L435 127 L452 120 L469 124 L486 119 L503 128 L519 91 L536 153 L553 61 L570 183 L587 78 L604 167 L620 103 L637 140 L654 111 L671 132 L688 116 L705 126 L721 120 L738 123 L755 121 L772 122 L900 122"
                    />
                  </svg>
                  <div className="signal-readout"><strong>−12.8</strong><span>dBFS<br />peak</span></div>
                </div>

                <div className="signal-frame" data-signal-frame>
                  <p className="signal-state">decoder / local</p>
                  <div className="token-field">
                    <span>make</span><span>the</span><span>interface</span><span>feel</span>
                    <span>immediate</span><span>and</span><span>keep</span><span>the</span>
                    <span>transcript</span><span>on</span><span>this</span><span>machine</span>
                  </div>
                  <p className="decoder-device">/dev/nvidia0</p>
                </div>

                <div className="signal-frame" data-signal-frame>
                  <p className="signal-state">clipboard / ready</p>
                  <blockquote>
                    “make the interface feel immediate and keep the transcript
                    on this machine”<span className="text-cursor" />
                  </blockquote>
                  <div className="paste-status"><span>focus restored</span><span>submit: false</span></div>
                </div>
              </div>
              <div className="signal-progress"><span data-signal-progress /></div>
              <p className="stage-caption">live model of the local signal path / scroll to advance</p>
            </div>

            <ol className="process-steps">
              {processSteps.map((step, index) => (
                <li
                  className={index === 0 ? "is-active" : ""}
                  data-process-step
                  id={`step-${step.label}`}
                  key={step.label}
                >
                  <div className="step-id"><span>{step.number}</span><span>{step.label}</span></div>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                  <code>{step.meta}</code>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="install" id="install" aria-labelledby="install-title">
          <div className="install-stamp" aria-hidden="true" data-install-stamp>
            <span>V</span><span>O</span><span>X</span>
          </div>

          <div className="install-heading" data-reveal>
            <p className="section-label"><span>02</span> bootstrap</p>
            <h2 id="install-title">built for one<br />machine. yours.</h2>
            <p>
              An open-source prototype for Cinnamon on X11, PipeWire and NVIDIA
              CUDA. Read it, build it, make it yours.
            </p>
          </div>

          <div className="install-panel" data-reveal>
            <div className="install-panel-head">
              <span>quick start / bash</span>
              <span>01—02</span>
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

          <footer className="install-footer" data-reveal>
            <MotionLink className="action action-dark" href={`${repository}#install-and-start-using-vox`}>
              open the install guide <span aria-hidden="true">↗</span>
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
