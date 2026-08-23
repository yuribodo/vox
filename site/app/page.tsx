import { CopyCommand } from "../components/CopyCommand";
import { Waveform } from "../components/Waveform";

const repository = "https://github.com/yuribodo/vox";

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>

      <header className="site-header">
        <a className="brand" href="#top" aria-label="Vox home">
          <svg className="brand-mark" viewBox="0 0 28 28" aria-hidden="true">
            <path d="M4 9v10M9 5v18M14 2v24M19 7v14M24 10v8" />
          </svg>
          <span>vox</span>
        </a>

        <output className="header-status" aria-label="Project status">
          <span className="status-light" />
          <span>open source / v0.1.0</span>
        </output>

        <a className="header-link" href={repository}>GitHub <span aria-hidden="true">↗</span></a>
      </header>

      <main id="main">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero-copy reveal">
            <p className="eyebrow"><span>~/voice/input</span> Local Linux dictation</p>
            <h1 id="hero-title">Say it.<br />See it.<br /><em>Send it.</em></h1>
            <p className="hero-description">
              Push-to-talk speech recognition for Linux. Vox captures your voice,
              runs Whisper locally, and pastes the result exactly where you started.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href={`${repository}#install-and-start-using-vox`}>
                <span className="button-prompt">$</span> install vox
              </a>
              <a className="button button-secondary" href={repository}>view source <span aria-hidden="true">↗</span></a>
            </div>
            <p className="safety-note"><span aria-hidden="true">■</span> No cloud during dictation. No automatic Enter.</p>
          </div>

          <div className="console-wrap reveal" data-delay="1">
            <div className="console" role="img" aria-label="Animated representation of a Vox recording session">
              <div className="console-bar">
                <div className="console-dots" aria-hidden="true"><i /><i /><i /></div>
                <span>vox — pipewire:alsa_input.usb</span>
                <span className="console-mode">REC</span>
              </div>

              <div className="console-screen">
                <div className="console-meta"><span>CH_01 / 16KHZ / MONO</span><span>LOCAL_ONLY</span></div>
                <div className="scope" aria-hidden="true">
                  <Waveform />
                  <span className="scope-axis axis-y">+1.0<br /><br />0.0<br /><br />−1.0</span>
                  <span className="scope-axis axis-x">00:00:06:18</span>
                </div>

                <div className="transcript-preview">
                  <span className="prompt" aria-hidden="true">›</span>
                  <p>make the interaction feel immediate and keep the transcript on this machine<span className="cursor" aria-hidden="true" /></p>
                </div>

                <div className="console-footer">
                  <span><i className="rec-dot" aria-hidden="true" /> listening</span>
                  <span>large-v3-turbo / cuda</span>
                  <span className="timer">00:06</span>
                </div>
              </div>
            </div>
            <p className="console-caption"><span>FIG. 01</span> The Flow Bar listens. Your machine does the rest.</p>
          </div>

          <a className="scroll-cue" href="#signal" aria-label="Continue to how Vox works">
            <span>scroll to inspect</span><i aria-hidden="true" />
          </a>
        </section>

        <section className="signal-section" id="signal" aria-labelledby="signal-title">
          <div className="section-heading reveal">
            <p className="section-index">01 / signal path</p>
            <h2 id="signal-title">One shortcut.<br />Zero round trips.</h2>
            <p>Audio becomes text without leaving the workstation.</p>
          </div>

          <div className="signal-grid reveal" data-delay="1">
            <article className="signal-step">
              <div className="step-top"><span>01</span><span>CAPTURE</span></div>
              <div className="step-visual capture-visual" aria-hidden="true">
                {Array.from({ length: 11 }, (_, index) => <span key={index} />)}
              </div>
              <h3>Speak naturally.</h3>
              <p>Press <kbd>Super</kbd> + <kbd>V</kbd>. PipeWire records clean mono audio while the Flow Bar shows the live level.</p>
              <code>16 kHz / PCM WAV</code>
            </article>

            <article className="signal-step feature-step">
              <div className="step-top"><span>02</span><span>DECODE</span></div>
              <div className="step-visual decode-visual" aria-hidden="true">
                <div className="model-core">W</div>
                <div className="orbit orbit-one" />
                <div className="orbit orbit-two" />
                <i className="node n1" /><i className="node n2" /><i className="node n3" />
              </div>
              <h3>Transcribe locally.</h3>
              <p>Whisper large-v3-turbo and Silero VAD run on your NVIDIA GPU. Dictation stays yours.</p>
              <code>whisper.cpp / CUDA</code>
            </article>

            <article className="signal-step">
              <div className="step-top"><span>03</span><span>INSERT</span></div>
              <div className="step-visual insert-visual" aria-hidden="true">
                <span className="insert-line" /><span className="insert-line short" />
                <span className="insert-line" /><span className="insert-cursor" />
              </div>
              <h3>Review, then send.</h3>
              <p>Vox returns to the field you started from and pastes the transcript. It never presses Enter.</p>
              <code>Ctrl+V / no submit</code>
            </article>
          </div>
        </section>

        <section className="install-section" id="install" aria-labelledby="install-title">
          <div className="install-background" aria-hidden="true">VOX</div>
          <div className="install-copy reveal">
            <p className="section-index">02 / bootstrap</p>
            <h2 id="install-title">Your voice.<br />Your silicon.</h2>
            <p>A focused prototype for Cinnamon on X11, built for people who like knowing exactly where their data goes.</p>
          </div>

          <div className="install-terminal reveal" data-delay="1">
            <div className="install-label"><span>QUICK START</span><span>bash</span></div>
            <div className="command-row">
              <code><span>$</span> git clone https://github.com/yuribodo/vox.git <b>&amp;&amp;</b> cd vox</code>
              <CopyCommand command="git clone https://github.com/yuribodo/vox.git && cd vox" />
            </div>
            <div className="command-row secondary-command">
              <code><span>$</span> make build <b>&amp;&amp;</b> make fetch-whisper <b>&amp;&amp;</b> make doctor</code>
              <CopyCommand command="make build && make fetch-whisper && make doctor" />
            </div>
            <div className="requirements">
              <span>Cinnamon / X11</span><span>PipeWire</span><span>NVIDIA CUDA</span><span>Go 1.26</span>
            </div>
          </div>

          <div className="install-footer reveal" data-delay="2">
            <a className="button button-primary" href={`${repository}#requirements`}>read the install guide <span aria-hidden="true">↗</span></a>
            <div className="footer-meta">
              <span>MIT licensed</span><span>made for Linux</span>
              <a href="third-party-licenses.txt">third-party licenses</a>
              <span>© 2026 Vox contributors</span>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
