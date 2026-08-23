"use client";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import type { ReactNode } from "react";
import { useEffect, useRef } from "react";

export function LandingMotion({ children }: Readonly<{ children: ReactNode }>) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!rootRef.current) return;

    gsap.registerPlugin(ScrollTrigger);

    const context = gsap.context(() => {
      const media = gsap.matchMedia();

      media.add("(prefers-reduced-motion: no-preference)", () => {
        const path = document.querySelector<SVGPathElement>("[data-signal-path]");
        const status = document.querySelector<HTMLElement>("[data-signal-status]");
        const transcriptLines = gsap.utils.toArray<SVGPathElement>("[data-transcript-lines] path");
        const result = document.querySelector<HTMLElement>("[data-signal-result]");

        if (path) {
          const length = path.getTotalLength();
          gsap.set(path, { strokeDasharray: length, strokeDashoffset: length });
        }

        gsap.set(transcriptLines, { scaleX: 0, autoAlpha: 0, transformOrigin: "left center" });
        gsap.set("[data-processor]", { autoAlpha: 0.3 });
        if (result) gsap.set(result, { y: 6, autoAlpha: 0 });
        if (status) status.textContent = "capturing / 16 kHz";

        const intro = gsap.timeline({ defaults: { ease: "power3.out" } });
        intro
          .from("[data-header]", { y: -8, autoAlpha: 0, duration: 0.42 })
          .from(".eyebrow", { y: 8, autoAlpha: 0, duration: 0.42 }, 0.1)
          .from("[data-hero-line]", {
            yPercent: 108,
            duration: 0.72,
            stagger: 0.075,
            ease: "power4.out",
          }, 0.16)
          .from(".hero-description", { y: 12, autoAlpha: 0, duration: 0.52 }, 0.42)
          .from(".hero-actions", { y: 10, autoAlpha: 0, duration: 0.48 }, 0.49)
          .from("[data-signal]", { y: 14, scale: 0.995, autoAlpha: 0, duration: 0.62 }, 0.55);

        const signal = gsap.timeline({ delay: 0.7 });
        if (path) {
          signal.to(path, { strokeDashoffset: 0, duration: 0.9, ease: "power2.out" });
        }
        signal
          .call(() => {
            if (status) status.textContent = "transcribing / local GPU";
          })
          .to("[data-processor]", { autoAlpha: 1, duration: 0.24, ease: "power3.out" })
          .from(".processor-ring", {
            scale: 0.86,
            transformOrigin: "center",
            duration: 0.45,
            ease: "power3.out",
          }, "<")
          .from(".processor-core", {
            scale: 0.6,
            transformOrigin: "center",
            duration: 0.34,
            ease: "power3.out",
          }, "<0.06")
          .to(transcriptLines, {
            scaleX: 1,
            autoAlpha: 1,
            duration: 0.46,
            stagger: 0.055,
            ease: "power3.out",
          }, "-=0.08")
          .call(() => {
            if (status) status.textContent = "ready / clipboard";
          })
          .to(result, { y: 0, autoAlpha: 1, duration: 0.24, ease: "power3.out" });

        gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((element) => {
          const targets = element.children.length > 1 ? Array.from(element.children) : element;
          gsap.from(targets, {
            y: 12,
            autoAlpha: 0,
            duration: 0.44,
            stagger: 0.05,
            ease: "power3.out",
            scrollTrigger: { trigger: element, start: "top 88%", once: true },
          });
        });

        gsap.from("[data-detail]", {
            y: 10,
            autoAlpha: 0,
            duration: 0.44,
            stagger: 0.05,
            ease: "power3.out",
          scrollTrigger: { trigger: ".detail-list", start: "top 86%", once: true },
        });
      });

      return () => media.revert();
    }, rootRef);

    return () => context.revert();
  }, []);

  return <div ref={rootRef}>{children}</div>;
}
