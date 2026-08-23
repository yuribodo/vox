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
        const intro = gsap.timeline({ defaults: { ease: "power3.out" } });
        intro
          .from("[data-specimen]", { clipPath: "inset(0 100% 0 0)", duration: 1.15 })
          .from("[data-intro]", { y: 18, autoAlpha: 0, duration: 0.65, stagger: 0.06 }, "-=0.68")
          .from(".hero-calibration i", { scaleX: 0, duration: 0.7 }, "-=0.4");

        gsap.to("[data-specimen]", {
          yPercent: -3,
          rotate: 0.5,
          ease: "none",
          scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: 0.6 },
        });

        gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((element) => {
          gsap.from(element, {
            y: 20,
            autoAlpha: 0,
            duration: 0.72,
            ease: "power3.out",
            scrollTrigger: { trigger: element, start: "top 86%", once: true },
          });
        });

        gsap.utils.toArray<HTMLElement>("[data-section-image]").forEach((figure) => {
          const image = figure.querySelector<HTMLElement>("[data-image-inner]");
          const timeline = gsap.timeline({
            scrollTrigger: { trigger: figure, start: "top 82%", once: true },
          });

          timeline.from(figure, {
            clipPath: "inset(0 100% 0 0)",
            duration: 1.05,
            ease: "power3.inOut",
          });

          if (image) {
            timeline.from(image, { scale: 1.035, duration: 1.05, ease: "power3.out" }, 0);
          }
        });

        gsap.from("[data-step-list] li", {
          y: 14,
          autoAlpha: 0,
          duration: 0.58,
          stagger: 0.07,
          ease: "power3.out",
          scrollTrigger: { trigger: "[data-step-list]", start: "top 84%", once: true },
        });
      });

      return () => media.revert();
    }, rootRef);

    return () => context.revert();
  }, []);

  return <div ref={rootRef}>{children}</div>;
}
