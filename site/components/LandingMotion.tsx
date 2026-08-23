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
        gsap.from("[data-intro]", {
          y: 12,
          autoAlpha: 0,
          duration: 0.55,
          stagger: 0.055,
          ease: "power3.out",
        });

        const path = document.querySelector<SVGPathElement>("[data-signal-path]");
        if (path) {
          const length = path.getTotalLength();
          gsap.set(path, { strokeDasharray: length, strokeDashoffset: length });
          gsap.to(path, { strokeDashoffset: 0, duration: 1.1, delay: 0.3, ease: "power2.out" });
        }

        gsap.from("[data-signal-dot]", {
          scale: 0.92,
          autoAlpha: 0,
          transformOrigin: "center",
          duration: 0.35,
          delay: 1,
          ease: "power3.out",
        });

        gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((element) => {
          gsap.from(element, {
            y: 16,
            autoAlpha: 0,
            duration: 0.5,
            ease: "power3.out",
            scrollTrigger: { trigger: element, start: "top 88%", once: true },
          });
        });

        gsap.from("[data-detail]", {
          y: 12,
          autoAlpha: 0,
          duration: 0.45,
          stagger: 0.06,
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
