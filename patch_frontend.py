import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Overlap fix
old_card = """                <div class="bg-dark-surface border border-brand-500/30 rounded-xl p-6 relative overflow-hidden glow-brand">
                    <div class="absolute top-0 right-0 p-4">
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-brand-500/10 text-brand-500 border border-brand-500/30">
                            Ensemble Blend
                        </span>
                    </div>
                    <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">AETHER Dynamic Forecast</p>
                    <div class="mt-4 flex items-baseline">
                        <span id="blendTemp" class="text-5xl font-extrabold text-white tracking-tight">--</span>
                        <span class="ml-1 text-2xl font-semibold text-gray-400">°C</span>
                    </div>
                    <p id="blendLocationTime" class="mt-2 text-xs text-gray-400 flex items-center">
                        <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                        <span>Select a target and run</span>
                    </p>
                </div>"""

new_card = """                <div class="bg-dark-surface border border-brand-500/30 rounded-xl p-6 relative overflow-hidden glow-brand flex flex-col justify-between">
                    <div class="flex justify-between items-start mb-2">
                        <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mt-1">AETHER Dynamic Forecast</p>
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-brand-500/10 text-brand-500 border border-brand-500/30 whitespace-nowrap ml-2">
                            Ensemble Blend
                        </span>
                    </div>
                    <div class="flex items-baseline mb-2">
                        <span id="blendTemp" class="text-5xl leading-none font-extrabold text-white tracking-tight">--</span>
                        <span class="ml-1 text-2xl font-semibold text-gray-400">°C</span>
                    </div>
                    <p id="blendLocationTime" class="text-xs text-gray-400 flex items-center mb-4">
                        <svg class="w-3.5 h-3.5 mr-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                        <span class="truncate">Select a target and run</span>
                    </p>
                    <button id="explainBtn" class="hidden w-fit flex items-center space-x-1.5 text-xs text-brand-400 hover:text-brand-300 transition-colors font-medium px-3 py-1.5 rounded-lg bg-brand-500/10 border border-brand-500/20 hover:bg-brand-500/20">
                        <span>🧠 Why this forecast?</span>
                    </button>
                </div>"""
html = html.replace(old_card, new_card)

# 2. Location expansion
old_locs = """                        <option value="17.4400,78.3400">Gachibowli (17.44°N, 78.34°E)</option>
                        <option value="17.4474,78.3762">HITEC City (17.45°N, 78.38°E)</option>
                        <option value="17.3850,78.4867">Hyderabad (17.39°N, 78.49°E)</option>
                        <option value="17.4399,78.4983">Secunderabad (17.44°N, 78.50°E)</option>"""

new_locs = """                        <option value="17.4400,78.3400">Gachibowli (17.44°N, 78.34°E)</option>
                        <option value="17.4474,78.3762">HITEC City (17.45°N, 78.38°E)</option>
                        <option value="17.4399,78.4983">Secunderabad (17.44°N, 78.50°E)</option>
                        <option value="17.3457,78.5522">LB Nagar (17.35°N, 78.55°E)</option>
                        <option value="17.3688,78.5307">Dilsukhnagar (17.37°N, 78.53°E)</option>
                        <option value="17.4156,78.4347">Banjara Hills (17.42°N, 78.43°E)</option>
                        <option value="17.3719,78.5085">Malakpet (17.37°N, 78.51°E)</option>
                        <option value="17.3371,78.5645">Vanasthalipuram (17.34°N, 78.56°E)</option>
                        <option value="17.4843,78.3889">Kukatpally (17.48°N, 78.39°E)</option>
                        <option value="17.4483,78.3905">Madhapur (17.45°N, 78.39°E)</option>
                        <option value="17.4326,78.4071">Jubilee Hills (17.43°N, 78.41°E)</option>
                        <option value="17.4375,78.4482">Ameerpet (17.44°N, 78.45°E)</option>
                        <option value="17.4423,78.4619">Begumpet (17.44°N, 78.46°E)</option>
                        <option value="17.3934,78.4338">Mehdipatnam (17.39°N, 78.43°E)</option>
                        <option value="17.4294,78.5385">Tarnaka (17.43°N, 78.54°E)</option>
                        <option value="17.4018,78.5602">Uppal (17.40°N, 78.56°E)</option>
                        <option value="17.4699,78.3618">Kondapur (17.47°N, 78.36°E)</option>
                        <option value="17.4988,78.3458">Miyapur (17.50°N, 78.35°E)</option>
                        <option value="17.3986,78.3968">Manikonda (17.40°N, 78.40°E)</option>
                        <option value="17.3888,78.4716">Nampally (17.39°N, 78.47°E)</option>
                        <option value="17.3879,78.4754">Abids (17.39°N, 78.48°E)</option>
                        <option value="17.3846,78.4848">Koti (17.38°N, 78.48°E)</option>
                        <option value="17.3616,78.4747">Charminar (17.36°N, 78.47°E)</option>"""
html = html.replace(old_locs, new_locs)

# 3. Add Transparency Panel HTML
transparency_html = """
    <!-- Transparency Modal -->
    <div id="transparencyOverlay" class="fixed inset-0 bg-black/80 z-50 hidden backdrop-blur-sm transition-opacity flex items-center justify-center p-4 overflow-y-auto">
        <div id="transparencyModal" class="bg-dark-surface border border-brand-500/30 rounded-2xl shadow-2xl w-full max-w-3xl my-auto transform transition-transform scale-95 opacity-0 overflow-hidden flex flex-col max-h-[90vh]">
            <!-- Header -->
            <div class="px-6 py-5 border-b border-white/10 bg-dark-card flex justify-between items-center sticky top-0 z-10">
                <div class="flex items-center space-x-3">
                    <span class="text-2xl">🧠</span>
                    <h2 class="text-xl font-bold text-white tracking-tight">AETHER Decision Transparency</h2>
                </div>
                <button id="closeTransparencyBtn" class="text-gray-400 hover:text-white p-2 rounded-full bg-black/20 hover:bg-black/40 transition-colors focus:outline-none">
                    <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            
            <!-- Body -->
            <div class="p-6 overflow-y-auto w-full space-y-8 pb-10">
                
                <!-- Section 1 & 2: Context and Inputs -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-dark-card border border-dark-border rounded-xl p-5">
                        <h3 class="text-xs font-semibold text-brand-400 uppercase tracking-widest mb-4">1. Forecast Context</h3>
                        <div class="space-y-3 text-sm text-gray-300">
                            <div class="flex justify-between border-b border-dark-border/50 pb-2">
                                <span class="text-gray-500">Location</span>
                                <span id="transLocation" class="font-medium text-white text-right">--</span>
                            </div>
                            <div class="flex justify-between border-b border-dark-border/50 pb-2">
                                <span class="text-gray-500">Coordinates</span>
                                <span id="transCoords" class="code-font text-white">--</span>
                            </div>
                            <div class="flex justify-between border-b border-dark-border/50 pb-2">
                                <span class="text-gray-500">Valid Time</span>
                                <span id="transValidTime" class="font-medium text-white">--</span>
                            </div>
                            <div class="flex justify-between pb-1">
                                <span class="text-gray-500">Lead Time</span>
                                <span id="transLeadTime" class="font-medium text-white">-- hrs</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="bg-dark-card border border-dark-border rounded-xl p-5">
                        <h3 class="text-xs font-semibold text-brand-400 uppercase tracking-widest mb-4">2. NWP Model Inputs</h3>
                        <div class="space-y-3 text-sm text-gray-300">
                            <div class="flex justify-between items-center border-b border-dark-border/50 pb-2">
                                <span class="text-blue-400 font-medium">ECMWF IFS</span>
                                <span id="transIfsVal" class="text-white code-font bg-black/30 px-2 py-0.5 rounded">-- °C</span>
                            </div>
                            <div class="flex justify-between items-center border-b border-dark-border/50 pb-2">
                                <span class="text-amber-400 font-medium">NOAA GFS</span>
                                <span id="transGfsVal" class="text-white code-font bg-black/30 px-2 py-0.5 rounded">-- °C</span>
                            </div>
                            <div class="flex justify-between items-center pb-1">
                                <span class="text-emerald-400 font-medium">DWD ICON</span>
                                <span id="transIconVal" class="text-white code-font bg-black/30 px-2 py-0.5 rounded">-- °C</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Section 3 & 4: Weights & Methodology -->
                <div class="bg-dark-card border border-dark-border rounded-xl p-5">
                    <h3 class="text-xs font-semibold text-brand-400 uppercase tracking-widest mb-4">3. Dynamic Model Weights & Blending</h3>
                    <p class="text-sm text-gray-300 mb-5 leading-relaxed">
                        AETHER combines the individual NWP forecasts using dynamically learned model weights. Each model's contribution is adjusted according to the forecast context and learned model reliability.
                    </p>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-2">
                        <!-- Weight Bars -->
                        <div class="space-y-2">
                            <div class="flex justify-between text-xs font-medium">
                                <span class="text-gray-400">IFS Weight</span>
                                <span id="transIfsWeight" class="text-blue-400 code-font">--%</span>
                            </div>
                            <div class="h-2 bg-black/50 rounded-full overflow-hidden">
                                <div id="transIfsBar" class="h-full bg-blue-500 rounded-full" style="width: 0%"></div>
                            </div>
                        </div>
                        <div class="space-y-2">
                            <div class="flex justify-between text-xs font-medium">
                                <span class="text-gray-400">GFS Weight</span>
                                <span id="transGfsWeight" class="text-amber-400 code-font">--%</span>
                            </div>
                            <div class="h-2 bg-black/50 rounded-full overflow-hidden">
                                <div id="transGfsBar" class="h-full bg-amber-500 rounded-full" style="width: 0%"></div>
                            </div>
                        </div>
                        <div class="space-y-2">
                            <div class="flex justify-between text-xs font-medium">
                                <span class="text-gray-400">ICON Weight</span>
                                <span id="transIconWeight" class="text-emerald-400 code-font">--%</span>
                            </div>
                            <div class="h-2 bg-black/50 rounded-full overflow-hidden">
                                <div id="transIconBar" class="h-full bg-emerald-500 rounded-full" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 5: Transparent Calculation -->
                <div class="bg-black/30 border border-brand-500/20 rounded-xl p-5 relative overflow-hidden">
                    <div class="absolute inset-0 bg-gradient-to-r from-brand-900/10 to-transparent pointer-events-none"></div>
                    <h3 class="text-xs font-semibold text-brand-400 uppercase tracking-widest mb-4">4. Transparent Blend Calculation</h3>
                    
                    <div class="font-mono text-sm md:text-base text-gray-300 space-y-3 bg-black/40 p-5 rounded-lg border border-dark-border/50">
                        <div class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 items-center">
                             <div class="text-right text-gray-400"></div>
                             <div id="calcIfs" class="text-blue-300">(-- °C × --)</div>
                             
                             <div class="text-right text-gray-400 font-bold">+</div>
                             <div id="calcGfs" class="text-amber-300">(-- °C × --)</div>
                             
                             <div class="text-right text-gray-400 font-bold">+</div>
                             <div id="calcIcon" class="text-emerald-300">(-- °C × --)</div>
                             
                             <div class="text-right text-gray-400 font-bold mt-2 pt-2 border-t border-dark-border/50">=</div>
                             <div id="calcResult" class="text-white font-bold text-lg md:text-xl mt-2 pt-2 border-t border-dark-border/50">-- °C</div>
                        </div>
                    </div>
                </div>

                <!-- Section 6 & 7: Uncertainty & Provenance -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-dark-card border border-dark-border rounded-xl p-5">
                        <h3 class="text-xs font-semibold text-brand-400 uppercase tracking-widest mb-3">5. Uncertainty & Agreement</h3>
                        <p class="text-xs text-gray-400 mb-4 leading-relaxed">
                            Uncertainty reflects the expected forecast error envelope, while model disagreement indicates how closely the individual NWP models agree.
                        </p>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="bg-black/30 p-3 rounded-lg border border-white/5">
                                <div class="text-[10px] text-gray-500 uppercase font-semibold mb-1">Uncertainty</div>
                                <div id="transUncertainty" class="text-white font-semibold flex items-baseline">-- <span class="text-xs ml-1 text-gray-400">°C</span></div>
                            </div>
                            <div class="bg-black/30 p-3 rounded-lg border border-white/5">
                                <div class="text-[10px] text-gray-500 uppercase font-semibold mb-1">Disagreement</div>
                                <div id="transDisagreement" class="text-white font-semibold flex items-baseline">-- <span class="text-xs ml-1 text-gray-400">std</span></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="bg-dark-card border border-dark-border rounded-xl p-5 flex flex-col justify-between">
                        <div>
                            <h3 class="text-xs font-semibold text-brand-400 uppercase tracking-widest mb-3">6. Provenance & Confidence</h3>
                            <div class="flex justify-between items-center mb-3">
                                <span class="text-sm text-gray-400">Neural Confidence</span>
                                <span id="transConfidence" class="text-sm font-semibold text-white bg-brand-500/20 text-brand-400 px-2 py-1 rounded">--</span>
                            </div>
                        </div>
                        <div id="refContainer" class="hidden border-t border-dark-border/50 pt-3 mt-3">
                            <div class="flex justify-between items-center">
                                <span class="text-xs text-gray-500 font-medium">Reference / Verification Value</span>
                                <span id="transRefValue" class="text-sm font-semibold text-white code-font bg-black/40 px-2 py-1 rounded">-- °C</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Disclaimer -->
                <div class="text-center mt-6">
                    <p class="text-[10px] text-gray-500 leading-relaxed max-w-2xl mx-auto italic">
                        Decision transparency shows the observable forecast inputs, model contributions, ensemble calculation and uncertainty. It does not expose private model chain-of-thought.
                    </p>
                </div>
            </div>
        </div>
    </div>
"""
# Insert before main closes or before scripts
html = html.replace('</main>', '</main>' + transparency_html)

# Add logic for mapping data and opening/closing transparency
js_patch = """
        // Transparency Logic
        let lastApiData = null;
        
        function setupTransparency() {
            const explainBtn = document.getElementById('explainBtn');
            const overlay = document.getElementById('transparencyOverlay');
            const modal = document.getElementById('transparencyModal');
            const closeBtn = document.getElementById('closeTransparencyBtn');
            
            function openModal() {
                if(!lastApiData) return;
                populateTransparency(lastApiData);
                overlay.classList.remove('hidden');
                // trigger animation
                setTimeout(() => {
                    modal.classList.remove('scale-95', 'opacity-0');
                    modal.classList.add('scale-100', 'opacity-100');
                }, 10);
            }
            
            function closeModal() {
                modal.classList.remove('scale-100', 'opacity-100');
                modal.classList.add('scale-95', 'opacity-0');
                setTimeout(() => {
                    overlay.classList.add('hidden');
                }, 300);
            }
            
            explainBtn.addEventListener('click', openModal);
            closeBtn.addEventListener('click', closeModal);
            overlay.addEventListener('click', (e) => {
                if(e.target === overlay) closeModal();
            });
            document.addEventListener('keydown', (e) => {
                if(e.key === 'Escape' && !overlay.classList.contains('hidden')) {
                    closeModal();
                }
            });
        }
        
        function populateTransparency(data) {
            const locName = document.getElementById('locationSelect').selectedOptions[0].text.split('(')[0].trim();
            const lat = data.location.latitude;
            const lon = data.location.longitude;
            
            document.getElementById('transLocation').innerText = locName;
            document.getElementById('transCoords').innerText = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
            
            // Format time nicely
            const d = new Date(data.valid_time);
            document.getElementById('transValidTime').innerText = d.toLocaleString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'});
            document.getElementById('transLeadTime').innerText = data.lead_time_hours;
            
            const f = data.model_forecasts || {};
            const w = data.model_weights || {};
            
            document.getElementById('transIfsVal').innerText = (f.IFS !== undefined ? f.IFS.toFixed(2) : '--') + " °C";
            document.getElementById('transGfsVal').innerText = (f.GFS !== undefined ? f.GFS.toFixed(2) : '--') + " °C";
            document.getElementById('transIconVal').innerText = (f.ICON !== undefined ? f.ICON.toFixed(2) : '--') + " °C";
            
            const wIfs = (w.IFS || 0);
            const wGfs = (w.GFS || 0);
            const wIcon = (w.ICON || 0);
            
            // Weights Bars
            document.getElementById('transIfsWeight').innerText = (wIfs * 100).toFixed(1) + "%";
            document.getElementById('transIfsBar').style.width = (wIfs * 100) + "%";
            
            document.getElementById('transGfsWeight').innerText = (wGfs * 100).toFixed(1) + "%";
            document.getElementById('transGfsBar').style.width = (wGfs * 100) + "%";
            
            document.getElementById('transIconWeight').innerText = (wIcon * 100).toFixed(1) + "%";
            document.getElementById('transIconBar').style.width = (wIcon * 100) + "%";
            
            // Equation 
            const ifsVal = f.IFS || 0;
            const gfsVal = f.GFS || 0;
            const iconVal = f.ICON || 0;
            
            document.getElementById('calcIfs').innerText = `(${ifsVal.toFixed(2)} °C × ${wIfs.toFixed(3)})`;
            document.getElementById('calcGfs').innerText = `(${gfsVal.toFixed(2)} °C × ${wGfs.toFixed(3)})`;
            document.getElementById('calcIcon').innerText = `(${iconVal.toFixed(2)} °C × ${wIcon.toFixed(3)})`;
            
            document.getElementById('calcResult').innerText = data.forecast.toFixed(2) + " °C";
            
            // Uncertainty
            document.getElementById('transUncertainty').innerHTML = `±${data.uncertainty.toFixed(2)} <span class="text-xs ml-1 text-gray-400">°C</span>`;
            document.getElementById('transDisagreement').innerHTML = `${data.disagreement.toFixed(2)} <span class="text-xs ml-1 text-gray-400">std</span>`;
            document.getElementById('transConfidence').innerText = data.confidence || "Unknown";
            
            // Provenance
            const refContainer = document.getElementById('refContainer');
            if(data.reference_value !== null && data.reference_value !== undefined) {
                refContainer.classList.remove('hidden');
                document.getElementById('transRefValue').innerText = data.reference_value.toFixed(2) + " °C";
            } else {
                refContainer.classList.add('hidden');
            }
        }
"""
html = html.replace('</script>\n</body>', js_patch + '\n    </script>\n</body>')

# In fetchForecast, save lastApiData and reveal explainBtn
update_render = """
        function renderForecast(data) {
            lastApiData = data;
            document.getElementById('explainBtn').classList.remove('hidden');
            
            document.getElementById('blendTemp').innerText = data.forecast.toFixed(2);"""
html = html.replace("""
        function renderForecast(data) {
            document.getElementById('blendTemp').innerText = data.forecast.toFixed(2);""", update_render.strip('\n'))

# Make sure initChart doesn't get messed up.
# Then add setupTransparency() invocation to window.onload.
init_call = """
        window.onload = () => {
            initDefaults();
            initChart(0, 0, 0, 0);
            setupTransparency();
            // Optionally auto-fetch initial forecast
            fetchForecast();
        };"""
html = html.replace("""
        window.onload = () => {
            initDefaults();
            initChart(0, 0, 0, 0);
            // Optionally auto-fetch initial forecast
            fetchForecast();
        };""", init_call.strip('\n'))

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
