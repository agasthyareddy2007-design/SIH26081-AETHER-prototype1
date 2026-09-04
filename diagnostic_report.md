## AETHER DYNAMIC BLENDING DIAGNOSTIC REPORT

### 1. CURRENT PERFORMANCE (Test Set)
- **IFS RMSE:** 1.2529
- **AIFS RMSE:** 2.4226
- **GFS RMSE:** 1.7573
- **Simple Average RMSE:** 0.9730
- **Dynamic Blend RMSE:** 1.1234
*(Dynamic blend is ~15.5% worse than simple average.)*

### 2. DIAGNOSTIC FINDINGS

**Predicted vs. Actual Error Distributions & Calibration**
Diagnostic runs on the chronological splits reveal a massive calibration collapse when advancing from Validation to Test data.
- **Validation Set Correlation:** The XGBoost error predictors learned the absolute error structures exceptionally well (IFS Correlation: 0.525; AIFS: 0.833).
- **Test Set Correlation:** The predictors entirely failed to generalize on unseen future data. IFS predicted vs. actual error correlation dropped to **-0.0058** (pure noise).
This proves the XGBoost regressors violently overfit to instantaneous temporal features (`hour_sin`, `doy_sin`) specific to the training weather regime, failing to predict forward-looking model reliability.

**Weight Distribution (Test Set)**
- **IFS Average Weight:** 46.4%
- **AIFS Average Weight:** 15.4%
- **GFS Average Weight:** 38.2% 
*(AIFS is severely penalized and suppressed.)*

### 3. WHY SIMPLE AVERAGE WINS (Error Complementarity)
The secret to the Simple Average's success lies in robust **Bias Cancellation (Error Complementarity)**.
- **Test Set Biases:** IFS (+0.45), AIFS (-1.35), GFS (+0.68).
- The arithmetic mean (33% each) perfectly blends the massive negative bias of AIFS with the positive biases of IFS and GFS. The Simple Average achieves a remarkably neutral combined bias of **-0.07**.

### 4. WEIGHTING FAILURE ANALYSIS
The current architecture predicts *Absolute Expected Error* ($\hat{e} = |\hat{y} - y_{ref}|$), bounds it, and applies inverse-error weighting ($w_i \propto 1 / \hat{e}_i$).
- **Structural Flaw:** Absolute-error weighting fundamentally destroys ensemble bias cancellation. Because AIFS has high overall variance and highest absolute error, the dynamic blender slashed its weight to 15%. 
- By suppressing the only negatively biased model, the dynamic blender was left dominated by over-forecasting models (IFS/GFS), resulting in a massive uncancelled positive bias (**+0.25**). 
- Tested alternatives on the validation set (Softmax error weighting, Temperature-Scaled inverse weighting, and Static Inverse Weighting) all suffered from this identical mathematical fallacy: they penalized absolute variance and destroyed bias complementarity.

### 5. FEATURE SUFFICIENCY
The current 13 features (sine/cosine temporal encodings, immediate spread, diff arrays) are **insufficient** to predict generalized forward reliability.
- They possess strictly instantaneous, localized context.
- There is zero awareness of historical spatial regime shifting or recent model drift.
- **Highest Value Missing Features:** `rolling_7d_bias`, `rolling_7d_mae` (calculated exclusively from historical timesteps), and explicit `latitude/longitude` coordinates to allow the model to recognize geographic spatial domains where specific models possess hardened bias offsets.

### 6. RECOMMENDED CHANGE
**Smallest Technically Justified Modification:**
Transition from *Absolute Error Regression* to a **Direct Convex-Optimization Engine**. 
Instead of mapping absolute errors to weights (which mathematically cannot comprehend complementary bias), replace the 3 independent XGBoost scalar regressors with a simple Neural Network (e.g., PyTorch MLP) featuring a 3-node `Softmax` output layer. 

- **Architecture:** `Features → MLP → Softmax(w_IFS, w_AIFS, w_GFS)`
- **Loss Function:** Train the network natively on the actual forecasting objective: $Loss = MSE(\sum(w_i \cdot x_i), \text{target})$.
- This explicitly honors the requirement $\sum w_i = 1$ entirely through learned ML logic, but by optimizing the target *directly*, the ML system mathematically realizes "If I assign weight to AIFS, it offsets the IFS bias!" allowing it to natively learn bias-cancellation behavior exactly like the simple average, but dynamically optimized per spatial feature.
*(Secondary necessity: Add rolling historical bias (t-1) and lat/lon features to grant the system awareness of recent spatial regimes).*

### 7. EXPECTED RISK
- **Risk:** Implementing a custom PyTorch model requires swapping the core blending estimator. A neural network demands careful learning-rate/batch-size scheduling compared to XGBoost's out-of-the-box robustness.
- **Mitigation:** The architecture can be extremely shallow (e.g. 2 hidden layers), guaranteeing rapid convergence and preventing overparameterization on the tabular dataset.
