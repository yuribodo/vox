# Copyright and license audit

Audit date: 2026-08-23

Version reviewed: 0.1.0 plus public website

## Result

No known copyright blocker was found for publishing the current repository
under the MIT License.

- The tracked tree contains no vendored dependency source, model weights,
  executable binaries, third-party fonts, screenshots, recordings, or other
  third-party media. The website favicon and waveform artwork are original
  project assets implemented as source SVG and CSS.
- The Next.js landing page downloads pinned npm dependencies during its build.
  Its static export redistributes portions of the MIT-licensed Next.js, React,
  and React DOM runtimes together with their complete license notices.
- The only copied foreign license blocks are the complete MIT notices for the
  client runtimes redistributed by the website; they are isolated in the
  public third-party license file rather than mixed into project source.
- Technical references are short paraphrases with source links; the repository
  does not reproduce papers, model cards, or upstream documentation.
- The local preparation script downloads pinned upstream artifacts into the
  ignored `.local/` directory. It does not add them to a source release.
- The upstream components used by that script have permissive licenses: MIT for
  whisper.cpp, Whisper/model repositories, and Silero VAD; BSD 3-Clause for
  CMake. Their attribution and distribution conditions are recorded in
  [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).
- Next.js, React, and React DOM are MIT-licensed. Their pinned versions and
  attributions are recorded in `THIRD_PARTY_NOTICES.md`, and the deployed site
  links a generated notice file covering every production npm dependency. A
  shorter source copy in `site/public/third-party-licenses.txt` covers the
  client runtimes during local development.

## Checks performed

- Reviewed every tracked source, website asset, documentation, workflow,
  benchmark, and configuration file for third-party notices and suspicious
  copied blocks.
- Enumerated tracked file types and verified that no binary or media asset is
  present.
- Reviewed the pinned dependencies and their upstream license pages.
- Removed internal product requirements, architectural decision records,
  rejected implementation code, and machine-specific inventory.
- Kept only sanitized aggregate benchmark evidence; private audio, manifests,
  transcripts, and machine-readable results remain ignored.

## Conditions for redistribution

Publishing this source tree under MIT requires preserving the root `LICENSE`.
The website export must preserve `third-party-licenses.txt`. A future binary or
model bundle must additionally include the exact notices and license texts for
every bundled upstream component. Go's license also applies to portions of
compiled Go executables. System packages merely invoked by Vox are not
distributed by this repository.

## Limits

This is an engineering review, not legal advice. Copyright clearance does not
clear patents or trademarks. In particular, the project name and logo, if one
is adopted, should receive a separate trademark search before a public launch.
Future contributions still require provenance review; contributors affirm that
right in [`CONTRIBUTING.md`](../CONTRIBUTING.md).
