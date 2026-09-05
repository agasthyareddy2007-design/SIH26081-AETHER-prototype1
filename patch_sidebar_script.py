import re
with open("frontend/index.html", "r") as f:
    content = f.read()

# Replace main tag beginning
old_main_open = '<main class="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-8">'
new_main_open = '''<!-- Mobile AETHER Toggle -->
    <button id="mobileAetherToggle" class="lg:hidden fixed bottom-6 right-6 z-50 h-14 w-14 bg-brand-500 text-white rounded-full shadow-[0_0_20px_rgba(20,184,166,0.4)] flex items-center justify-center focus:outline-none hover:scale-105 transition-transform">
        <span class="text-2xl">🤖</span>
    </button>

    <!-- Main Container -->
    <main class="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 flex flex-col lg:flex-row gap-8 relative items-start">
        <div class="flex-1 w-full space-y-8 min-w-0 mb-20 lg:mb-0">'''

content = content.replace(old_main_open, new_main_open)

# Find the chat mock panel and replace it with the new sidebar
chat_mock_regex = re.compile(r'<!-- Chat Mock / Fallback Panel -->.*?</section>', re.DOTALL)

sidebar_html = '''</div> <!-- End Left Dashboard -->

        <!-- Right: AETHER Sidebar -->
        <aside id="aetherSidebar" class="
            fixed inset-y-0 right-0 z-40 w-80 max-w-[85vw] transform translate-x-full transition-transform duration-300 ease-in-out
            lg:relative lg:translate-x-0 lg:w-96 lg:sticky lg:top-24 lg:z-10 lg:h-[700px]
            flex flex-col bg-dark-surface/95 backdrop-blur-xl border border-brand-500/30 lg:rounded-xl shadow-2xl lg:glow-brand overflow-hidden
        ">
            <!-- Close Button (Mobile Only) -->
            <button id="mobileAetherClose" class="lg:hidden absolute top-4 right-4 text-gray-400 hover:text-white p-2 rounded-full bg-black/20">
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
            
            <!-- Header -->
            <div class="p-5 border-b border-white/5 bg-gradient-to-r from-brand-900/40 to-transparent flex items-center space-x-3">
                 <div class="h-10 w-10 bg-brand-500/20 border border-brand-500/40 rounded-xl flex items-center justify-center text-brand-500 text-lg">
                    🌦️
                 </div>
                 <div>
                     <h2 class="text-base font-bold text-white tracking-tight">AETHER</h2>
                     <p class="text-[11px] text-brand-300 uppercase tracking-widest mt-0.5">AI Weather Intelligence Assistant</p>
                 </div>
            </div>

            <!-- Chat History -->
            <div class="flex-1 p-5 overflow-y-auto space-y-4 bg-black/20 pb-4">
                <!-- System Welcome Message -->
                <div class="flex space-x-3">
                    <div class="h-8 w-8 rounded-full bg-brand-500/20 border border-brand-500/40 flex items-center justify-center text-brand-500 flex-shrink-0 text-sm">
                        🤖
                    </div>
                    <div class="bg-dark-card border border-dark-border rounded-2xl p-4 text-sm text-gray-200 rounded-tl-sm shadow-lg leading-relaxed whitespace-pre-wrap">Hello! I’m AETHER, your AI weather intelligence assistant. 🌦️
I’m currently under development — please support us as we build me into a smarter weather companion! 💙🤖</div>
                </div>
            </div>

            <!-- Locked Input Area -->
            <div class="p-5 border-t border-white/5 bg-dark-card/50">
                <div class="relative">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
                    </div>
                    <input type="text" disabled class="block w-full pl-10 pr-12 py-3 rounded-lg bg-black/40 border border-dark-border text-gray-500 text-sm focus:outline-none cursor-not-allowed" placeholder="Conversational intelligence coming soon...">
                    <div class="absolute inset-y-0 right-0 pr-2 flex items-center">
                        <button disabled class="p-1.5 rounded-md bg-dark-border/50 text-gray-500 cursor-not-allowed">
                            <svg class="h-5 w-5 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
                        </button>
                    </div>
                </div>
                <p class="text-[10px] text-center text-gray-500 mt-3 font-semibold uppercase tracking-widest flex items-center justify-center space-x-1">
                    <span>🔒 Locked for development</span>
                </p>
            </div>
        </aside>

        <!-- Overlay for mobile drawer -->
        <div id="aetherOverlay" class="lg:hidden fixed inset-0 bg-black/60 z-30 hidden backdrop-blur-sm transition-opacity"></div>'''

content = chat_mock_regex.sub(sidebar_html, content)

# Inject JS for toggle
script_end_tag = '<!-- App Logic -->'
js_injection = '''<!-- App Logic -->
    <script>
        // Mobile Sidebar Toggle Logic
        const mobileToggle = document.getElementById('mobileAetherToggle');
        const mobileClose = document.getElementById('mobileAetherClose');
        const sidebar = document.getElementById('aetherSidebar');
        const overlay = document.getElementById('aetherOverlay');

        function toggleAether() {
            sidebar.classList.toggle('translate-x-full');
            overlay.classList.toggle('hidden');
        }

        if(mobileToggle && mobileClose && sidebar && overlay) {
            mobileToggle.addEventListener('click', toggleAether);
            mobileClose.addEventListener('click', toggleAether);
            overlay.addEventListener('click', toggleAether);
        }
    </script>
'''

content = content.replace(script_end_tag, js_injection)

with open("frontend/index.html", "w") as f:
    f.write(content)
