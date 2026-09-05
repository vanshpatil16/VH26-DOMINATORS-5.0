'use client';

import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

export function ParallaxComponent() {
  const parallaxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);

    const triggerElement = parallaxRef.current?.querySelector('[data-parallax-layers]');

    if (triggerElement) {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: triggerElement,
          start: "0% 0%",
          end: "100% 0%",
          scrub: 0
        }
      });

      const layers = [
        { layer: "1", yPercent: 60 },
        { layer: "2", yPercent: 45 },
        { layer: "3", yPercent: 25 },
        { layer: "4", yPercent: 10 }
      ];

      layers.forEach((layerObj, idx) => {
        tl.to(
          triggerElement.querySelectorAll(`[data-parallax-layer="${layerObj.layer}"]`),
          {
            yPercent: layerObj.yPercent,
            ease: "none"
          },
          idx === 0 ? undefined : "<"
        );
      });
    }

    return () => {
      ScrollTrigger.getAll().forEach(st => st.kill());
      if (triggerElement) gsap.killTweensOf(triggerElement);
    };
  }, []);

  return (
    <div className="parallax relative w-full overflow-hidden bg-[#08090a]" ref={parallaxRef}>
      <section className="parallax__header relative w-full h-[85vh] md:h-screen flex items-center justify-center overflow-hidden">
        <div className="parallax__visuals relative w-full h-full flex items-center justify-center">
          {/* Top & Bottom Fade Masks */}
          <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-b from-[#08090a] via-[#08090a]/60 to-transparent z-20 pointer-events-none" />

          {/* Widescreen Layers */}
          <div data-parallax-layers className="parallax__layers relative w-full h-full flex items-center justify-center">
            {/* Background 16:9 Mesh Gradient Layer */}
            <img
              src="/parallax_bg_glow.jpg"
              loading="eager"
              data-parallax-layer="1"
              alt=""
              className="parallax__layer-img absolute inset-0 w-full h-full object-cover pointer-events-none opacity-80"
            />

            {/* Foreground 16:9 Glass & Particle Depth Layer */}
            <img
              src="/parallax_layer_depth.jpg"
              loading="eager"
              data-parallax-layer="2"
              alt=""
              className="parallax__layer-img absolute inset-0 w-full h-full object-cover pointer-events-none opacity-50 mix-blend-screen"
            />

            {/* Center Content & Title */}
            <div data-parallax-layer="3" className="parallax__layer-title relative z-30 text-center px-6 max-w-5xl mx-auto">
              <div className="inline-flex items-center space-x-2 bg-white/10 border border-white/20 backdrop-blur-md px-4 py-1.5 rounded-full text-xs font-mono text-cyan-300 mb-6 shadow-2xl">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                <span>PARALLAX MOTION ENGINE</span>
              </div>
              <h2 className="parallax__title text-5xl md:text-8xl font-semibold text-white tracking-tight drop-shadow-[0_10px_35px_rgba(0,0,0,0.9)] mb-4">
                Parallax Engineering
              </h2>
              <p className="text-zinc-300 text-sm md:text-lg font-mono tracking-wide max-w-2xl mx-auto drop-shadow-lg">
                Multi-layered depth and kinetic motion designed to align with modern team velocity.
              </p>
            </div>

            {/* Extra Ambient Lighting Layer */}
            <div
              data-parallax-layer="4"
              className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 via-purple-500/10 to-emerald-500/10 pointer-events-none mix-blend-color-dodge"
            />
          </div>

          <div className="parallax__fade absolute bottom-0 left-0 right-0 h-36 bg-gradient-to-t from-[#08090a] via-[#08090a]/70 to-transparent z-20 pointer-events-none" />
        </div>
      </section>

      {/* Footer SVG Symbol */}
      <section className="parallax__content relative py-14 flex justify-center items-center bg-[#08090a] border-t border-b border-white/10">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 160 160" fill="none" className="osmo-icon-svg text-zinc-500 hover:text-white transition-colors">
          <path d="M94.8284 53.8578C92.3086 56.3776 88 54.593 88 51.0294V0H72V59.9999C72 66.6273 66.6274 71.9999 60 71.9999H0V87.9999H51.0294C54.5931 87.9999 56.3777 92.3085 53.8579 94.8283L18.3431 130.343L29.6569 141.657L65.1717 106.142C67.684 103.63 71.9745 105.396 72 108.939V160L88.0001 160L88 99.9999C88 93.3725 93.3726 87.9999 100 87.9999H160V71.9999H108.939C105.407 71.9745 103.64 67.7091 106.12 65.1938L106.142 65.1716L141.657 29.6568L130.343 18.3432L94.8284 53.8578Z" fill="currentColor"></path>
        </svg>
      </section>
    </div>
  );
}
