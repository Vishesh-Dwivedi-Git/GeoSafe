import Navbar from "@/components/Navbar";

export default function HomePage() {
  return (
    <>
      <Navbar />

      {/* Hero Section */}
      <section className="relative min-h-screen flex flex-col items-center justify-center pt-16 overflow-hidden bg-black">
        {/* Globe Background Image - positioned at bottom */}
        <div className="absolute inset-x-0 bottom-0 z-0 h-[85%] pointer-events-none">
          <img
            alt="Earth from space with sunrise glow"
            className="w-full h-full object-cover"
            src="/earth-hero.png"
            style={{ objectPosition: "center 20%" }}
          />
          {/* Top fade: solid black into hero content */}
          <div className="absolute inset-0" style={{ background: "linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0.85) 15%, rgba(0,0,0,0.3) 40%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.4) 75%, rgba(0,0,0,0.95) 90%, rgba(0,0,0,1) 100%)" }} />
        </div>
        {/* Hero Content */}
        <div className="relative z-20 text-center px-4 max-w-4xl mx-auto">
          <h2 className="text-primary font-headline tracking-[0.3em] text-xs mb-6 opacity-80 uppercase">
            Hercules Platform Active
          </h2>
          <h1 className="text-5xl md:text-7xl font-headline font-bold text-white tracking-tight mb-8 leading-tight drop-shadow-2xl">
            AI-POWERED LAND RISK{" "}
            <span className="text-primary">INTELLIGENCE</span>
          </h1>
          <p className="text-on-surface-variant text-lg md:text-xl font-body max-w-2xl mx-auto mb-10 leading-relaxed opacity-90 drop-shadow-lg">
            From coordinates to compliance in seconds. Analyze orbital datasets
            with hyper-local intelligence for mission-critical land decisions.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
            <a href="/pipeline">
              <button className="group relative px-10 py-4 bg-primary text-on-primary font-headline font-extrabold tracking-widest rounded-lg transition-all duration-300 hover:shadow-[0_0_40px_rgba(58,223,250,0.3)] active:scale-95 cursor-pointer">
                ENTER COMMAND CENTER
              </button>
            </a>
            <a href="/dashboard">
              <button className="px-10 py-4 bg-white/5 backdrop-blur-md border border-white/10 text-white font-headline font-bold tracking-widest rounded-lg hover:bg-white/10 transition-all cursor-pointer">
                VIEW SYSTEM SPECS
              </button>
            </a>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="relative z-30 bg-black py-32 px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-end mb-20 gap-8">
            <div className="max-w-xl">
              <h3 className="text-primary font-headline tracking-widest text-xs uppercase mb-4">
                Core Capabilities
              </h3>
              <h2 className="text-4xl font-headline font-bold text-white">
                Planetary Data Synthesis
              </h2>
            </div>
            <div className="text-on-surface-variant font-body max-w-sm text-right opacity-80">
              Real-time telemetry meets legal scrutiny. Our AI clusters identify
              vulnerabilities before they impact your mission.
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Spatial Intelligence */}
            <div className="glass-panel p-8 rounded-xl flex flex-col group hover:bg-surface-container-highest transition-all duration-500">
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-8 text-primary group-hover:scale-110 transition-transform">
                <span className="material-symbols-outlined text-3xl">map</span>
              </div>
              <h4 className="text-xl font-headline font-bold text-white mb-4">
                Spatial Intelligence
              </h4>
              <p className="text-on-surface-variant text-sm leading-relaxed mb-8">
                High-resolution satellite imagery analysis combined with
                topographic sensor fusion for millimeter-accurate terrain
                modeling.
              </p>
              <div className="mt-auto pt-4 border-t border-outline-variant/30">
                <span className="text-primary font-headline text-xs tracking-widest uppercase cursor-pointer hover:underline">
                  Explore Layers
                </span>
              </div>
            </div>

            {/* AI Risk Classification */}
            <div className="glass-panel p-8 rounded-xl flex flex-col group hover:bg-surface-container-highest transition-all duration-500 border-primary/20">
              <div className="w-12 h-12 rounded-lg bg-tertiary/10 flex items-center justify-center mb-8 text-tertiary group-hover:scale-110 transition-transform">
                <span className="material-symbols-outlined text-3xl">
                  analytics
                </span>
              </div>
              <h4 className="text-xl font-headline font-bold text-white mb-4">
                AI Risk Classification
              </h4>
              <p className="text-on-surface-variant text-sm leading-relaxed mb-8">
                Automated threat detection using deep learning models trained on
                decades of environmental and geological historical datasets.
              </p>
              <div className="mt-auto">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-error-container/20 rounded-full">
                  <div className="w-2 h-2 rounded-full bg-error animate-pulse" />
                  <span className="text-[10px] font-headline text-error-dim font-bold tracking-widest">
                    REAL-TIME MONITORING
                  </span>
                </div>
              </div>
            </div>

            {/* Legal Insights */}
            <div className="glass-panel p-8 rounded-xl flex flex-col group hover:bg-surface-container-highest transition-all duration-500">
              <div className="w-12 h-12 rounded-lg bg-secondary/10 flex items-center justify-center mb-8 text-secondary group-hover:scale-110 transition-transform">
                <span className="material-symbols-outlined text-3xl">
                  description
                </span>
              </div>
              <h4 className="text-xl font-headline font-bold text-white mb-4">
                Legal Insights
              </h4>
              <p className="text-on-surface-variant text-sm leading-relaxed mb-8">
                Instant compliance mapping against local, regional, and
                international land-use regulations and heritage protection zones.
              </p>
              <div className="mt-auto pt-4 border-t border-outline-variant/30">
                <span className="text-primary font-headline text-xs tracking-widest uppercase cursor-pointer hover:underline">
                  Compliance Docs
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Telemetry Strip */}
      <div className="w-full bg-black py-4 px-8 border-y border-white/5">
        <div className="max-w-7xl mx-auto flex flex-wrap justify-between items-center gap-4">
          <div className="flex items-center gap-4">
            <span className="text-[10px] font-headline text-primary tracking-[0.4em] uppercase">
              Status
            </span>
            <span className="text-xs font-label text-slate-500 uppercase tracking-widest">
              System Nominal
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[10px] font-headline text-primary tracking-[0.4em] uppercase">
              Coord
            </span>
            <span className="text-xs font-label text-slate-500 uppercase tracking-widest">
              37.7749° N, 122.4194° W
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[10px] font-headline text-primary tracking-[0.4em] uppercase">
              Latency
            </span>
            <span className="text-xs font-label text-slate-500 uppercase tracking-widest">
              42ms [Relay Alpha]
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[10px] font-headline text-primary tracking-[0.4em] uppercase">
              Security
            </span>
            <span className="text-xs font-label text-slate-500 uppercase tracking-widest">
              Level 5 Encrypted
            </span>
          </div>
        </div>
      </div>

      {/* Data Visualization (Bento Preview) */}
      <section className="py-32 px-8 bg-black overflow-hidden">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-12 gap-6">
          <div className="md:col-span-8 bg-surface-container-low rounded-2xl overflow-hidden relative min-h-[400px] border border-white/5">
            <img
              alt="overhead high-angle satellite view of terrain"
              className="w-full h-full object-cover opacity-40 grayscale hover:grayscale-0 transition-all duration-700"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuBOA6N904jzeMEX9MkoLUgDTQiZPpRRWhrrmhbm8cbeXGfNls_Kf0TwLJcUfROsFI-s0cVDUkVvCPC6jJdIx6myY0QfPuUS4tgQ8KSnMr3Y7hM2rKTwyZsw1TyrdVx7EwMPUEFzCv-lWCQDbZg9lOv7Pj0mDs9Ot1Qz50mFYE0nu_DkljNpWbRX1ReIkFsQt42VkAavKQ0jNTiCjqiwQ_Qkw1vju-E-GwX_eSGr8zwnH0IOq-Y-tusPyV8FwINA7jGeSv6oqgQ92bM"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black to-transparent" />
            <div className="absolute bottom-8 left-8">
              <h3 className="text-2xl font-headline font-bold text-white mb-2">
                Thermal Topography
              </h3>
              <p className="text-on-surface-variant text-sm max-w-sm">
                Sub-surface analysis detecting heat signatures and moisture
                density anomalies.
              </p>
            </div>
            {/* Scanning Effect */}
            <div
              className="absolute left-0 w-full h-[2px] bg-primary shadow-[0_0_15px_rgba(58,223,250,0.8)] scan-line"
              style={{ top: "30%" }}
            />
          </div>

          <div className="md:col-span-4 flex flex-col gap-6">
            <div className="flex-1 bg-surface-container-highest p-6 rounded-2xl border border-white/5">
              <h4 className="text-primary font-headline text-xs tracking-widest uppercase mb-6">
                Active Clusters
              </h4>
              <div className="space-y-4">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-on-surface-variant">North Basin</span>
                  <span className="text-white font-label">98.2%</span>
                </div>
                <div className="w-full bg-black h-1 rounded-full overflow-hidden">
                  <div className="bg-primary h-full w-[98%]" />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-on-surface-variant">South Ridge</span>
                  <span className="text-white font-label">45.7%</span>
                </div>
                <div className="w-full bg-black h-1 rounded-full overflow-hidden">
                  <div className="bg-tertiary h-full w-[45%]" />
                </div>
              </div>
            </div>
            <div className="flex-1 bg-surface-container-highest p-6 rounded-2xl border border-white/5 flex flex-col items-center justify-center text-center">
              <span className="material-symbols-outlined text-primary text-4xl mb-4">
                rocket_launch
              </span>
              <h4 className="text-white font-headline font-bold uppercase tracking-tight">
                Orbital Sync
              </h4>
              <p className="text-on-surface-variant text-[10px] uppercase tracking-widest mt-2">
                Next satellite pass: 14m 22s
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-black py-20 px-8 border-t border-white/5">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start gap-12">
          <div>
            <div className="text-2xl font-bold tracking-tighter text-primary font-headline mb-6 uppercase">
              GEOSAFE
            </div>
            <p className="text-on-surface-variant text-sm max-w-xs leading-relaxed opacity-80">
              Defining the next frontier of spatial compliance and land risk
              analysis for global infrastructure projects.
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-12">
            <div className="flex flex-col gap-4">
              <h5 className="text-white font-headline text-xs tracking-widest uppercase">
                System
              </h5>
              <a
                className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                href="#"
              >
                Architecture
              </a>
              <a
                className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                href="#"
              >
                Hercules Engine
              </a>
              <a
                className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                href="#"
              >
                API Docs
              </a>
            </div>
            <div className="flex flex-col gap-4">
              <h5 className="text-white font-headline text-xs tracking-widest uppercase">
                Company
              </h5>
              <a
                className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                href="#"
              >
                The Mission
              </a>
              <a
                className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                href="#"
              >
                Press Registry
              </a>
              <a
                className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                href="#"
              >
                Personnel
              </a>
            </div>
            <div className="flex flex-col gap-4">
              <h5 className="text-white font-headline text-xs tracking-widest uppercase">
                Legal
              </h5>
              <a
                className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                href="#"
              >
                Protocol 7-G
              </a>
              <a
                className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                href="#"
              >
                Privacy
              </a>
              <a
                className="text-on-surface-variant text-sm hover:text-primary transition-colors"
                href="#"
              >
                Security
              </a>
            </div>
          </div>
        </div>
        <div className="max-w-7xl mx-auto mt-20 pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4">
          <span className="text-[10px] font-label text-slate-500 uppercase tracking-widest">
            © 2024 GEOSAFE STRATEGIC SYSTEMS. All rights reserved.
          </span>
          <div className="flex gap-6">
            <span className="material-symbols-outlined text-slate-500 hover:text-primary cursor-pointer text-sm">
              terminal
            </span>
            <span className="material-symbols-outlined text-slate-500 hover:text-primary cursor-pointer text-sm">
              satellite_alt
            </span>
            <span className="material-symbols-outlined text-slate-500 hover:text-primary cursor-pointer text-sm">
              shield
            </span>
          </div>
        </div>
      </footer>
    </>
  );
}
