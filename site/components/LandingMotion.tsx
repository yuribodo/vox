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
        const intro = gsap.timeline({ defaults: { ease: "power4.out" } });
        intro
          .from("[data-hero-media]", {
            clipPath: "inset(0 0 100% 0)",
            scale: 1.035,
            duration: 1.25,
          })
          .from("[data-intro]", { y: -10, autoAlpha: 0, duration: 0.45 }, "-=0.72")
          .from(
            "[data-hero-copy]",
            { y: 28, autoAlpha: 0, duration: 0.7, stagger: 0.08 },
            "-=0.58",
          )
          .from(".readout-line i", { scaleX: 0, duration: 0.7 }, "-=0.45");

        gsap.to("[data-hero-media]", {
          scale: 1.075,
          yPercent: 4,
          ease: "none",
          scrollTrigger: {
            trigger: ".hero",
            start: "top top",
            end: "bottom top",
            scrub: 0.8,
          },
        });

        gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((element) => {
          gsap.from(element, {
            y: 26,
            autoAlpha: 0,
            duration: 0.7,
            ease: "power3.out",
            scrollTrigger: { trigger: element, start: "top 84%", once: true },
          });
        });

        gsap.utils.toArray<HTMLElement>("[data-flow-row]").forEach((row) => {
          const rule = row.querySelector<HTMLElement>(".flow-rule i");
          const content = row.querySelectorAll(".flow-number, h3, .flow-detail");
          const timeline = gsap.timeline({
            scrollTrigger: { trigger: row, start: "top 78%", once: true },
          });

          timeline.from(content, {
            y: 24,
            autoAlpha: 0,
            duration: 0.62,
            stagger: 0.06,
            ease: "power3.out",
          });

          if (rule) {
            timeline.from(rule, {
              scaleX: 0,
              transformOrigin: "left center",
              duration: 0.8,
              ease: "power3.inOut",
            }, 0);
          }
        });
      });

      return () => media.revert();
    }, rootRef);

    return () => context.revert();
  }, []);

  return <div ref={rootRef}>{children}</div>;
}
