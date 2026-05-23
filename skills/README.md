# Lighthouse Analyst Skills

This directory contains the runnable analyst skill instructions generated from `backend/seed.py`.
Each analysis has its own `SKILL.md` so Gemini-managed agents can load richer methodology than the short catalog description.

## Layout

- `AGENTS.md`: shared analyst house style and output rules.
- `<group-key>/<skill-key>/SKILL.md`: one skill per seeded analysis definition.

## Skill Index

### Acquisition & Onboarding

- `acquisition-onboarding/channel-attribution/SKILL.md` - Channel Attribution Analysis
- `acquisition-onboarding/install-to-registration-conversion/SKILL.md` - Install-to-Registration Conversion
- `acquisition-onboarding/ftue-funnel/SKILL.md` - First-Time User Experience (FTUE) Funnel
- `acquisition-onboarding/onboarding-completion-dropoff/SKILL.md` - Onboarding Completion Drop-off
- `acquisition-onboarding/time-to-first-value/SKILL.md` - Time-to-First-Value (TTFV)
- `acquisition-onboarding/source-medium-quality/SKILL.md` - Source/Medium Quality Analysis

### Engagement & Usage Patterns

- `engagement-patterns/dau-wau-mau-stickiness/SKILL.md` - DAU/WAU/MAU Stickiness
- `engagement-patterns/session-frequency-duration-depth/SKILL.md` - Session Frequency, Duration & Depth
- `engagement-patterns/feature-adoption-heatmap/SKILL.md` - Feature Adoption Heatmap
- `engagement-patterns/power-vs-casual-segmentation/SKILL.md` - Power vs. Casual User Segmentation
- `engagement-patterns/time-of-day-day-of-week-usage/SKILL.md` - Usage by Time-of-Day & Day-of-Week
- `engagement-patterns/session-interval/SKILL.md` - Session Interval (Time-Between-Sessions)
- `engagement-patterns/content-screen-consumption/SKILL.md` - Content & Screen Consumption
- `engagement-patterns/navigation-path-flow-sankey/SKILL.md` - Navigation Path Flow (Sankey)
- `engagement-patterns/dead-end-rage-tap/SKILL.md` - Dead-End & Rage Tap Analysis

### Retention & Churn

- `retention-churn/cohort-retention-curves/SKILL.md` - Cohort Retention Curves
- `retention-churn/rolling-vs-classic-retention/SKILL.md` - Rolling vs. Classic Retention
- `retention-churn/churn-prediction-survival/SKILL.md` - Churn Prediction & Survival Analysis
- `retention-churn/resurrection-analysis/SKILL.md` - Resurrected User Analysis
- `retention-churn/retention-by-segment/SKILL.md` - Retention by User Segment
- `retention-churn/n-day-activity-curves/SKILL.md` - N-Day Activity Curves
- `retention-churn/magic-number-analysis/SKILL.md` - Magic Number Engagement Analysis

### Monetization & Revenue

- `monetization-revenue/arpu-arppu-arpdau/SKILL.md` - ARPU / ARPPU / ARPDAU Metrics
- `monetization-revenue/conversion-to-payer-funnel/SKILL.md` - Conversion-to-Payer Funnel
- `monetization-revenue/time-to-first-purchase/SKILL.md` - Time-to-First-Purchase Duration
- `monetization-revenue/rfm-purchase-recency/SKILL.md` - Recency, Frequency, Monetary (RFM) Purchase Analysis
- `monetization-revenue/revenue-concentration-whale-curve/SKILL.md` - Revenue Concentration (Whale Curve)
- `monetization-revenue/price-sensitivity-elasticity/SKILL.md` - Price Sensitivity & Elasticity Modeling
- `monetization-revenue/sku-item-sales/SKILL.md` - SKU & In-App Item Sales
- `monetization-revenue/ltv-modeling/SKILL.md` - Lifetime Value (LTV) Modeling
- `monetization-revenue/ltv-to-cac-by-channel/SKILL.md` - LTV-to-CAC Ratio by Acquisition Channel
- `monetization-revenue/subscription-renewal-cancellation/SKILL.md` - Subscription Renewal & Cancellation Patterns
- `monetization-revenue/trial-to-paid-conversion/SKILL.md` - Trial-to-Paid Conversion Optimization
- `monetization-revenue/iap-basket-analysis/SKILL.md` - In-App Purchases Basket Analysis

### Funnel & Conversion

- `funnel-conversion/multi-step-conversion-funnel/SKILL.md` - Multi-Step Conversion Funnel
- `funnel-conversion/micro-conversion-tracking/SKILL.md` - Micro-Conversion Tracking
- `funnel-conversion/funnel-stage-dropoff/SKILL.md` - Funnel Stage Drop-off Metrics
- `funnel-conversion/funnel-comparison-by-segment/SKILL.md` - Funnel Comparison by Segment
- `funnel-conversion/cart-checkout-abandonment/SKILL.md` - Cart & Checkout Abandonment Analysis
- `funnel-conversion/paywall-hit-rate-conversion/SKILL.md` - Paywall Hit Rate & Conversion

### Segmentation & Personas

- `segmentation-personas/behavioral-clustering/SKILL.md` - Behavioral Clustering Analysis
- `segmentation-personas/rfm-segmentation/SKILL.md` - RFM Segment Profiling
- `segmentation-personas/psychographic-segmentation/SKILL.md` - Genre-Taste Profile Mapping
- `segmentation-personas/lifecycle-stage-segmentation/SKILL.md` - User Lifecycle Stage Analysis
- `segmentation-personas/motivational-segmentation/SKILL.md` - Motivational Segment Profiling
- `segmentation-personas/high-value-user-profiling/SKILL.md` - High-Value User Profiling

### A/B Testing & Experimentation

- `ab-testing-experimentation/controlled-experiment-analysis/SKILL.md` - Controlled Experiment (A/B Test) Analysis
- `ab-testing-experimentation/multi-armed-bandit-optimization/SKILL.md` - Multi-Armed Bandit Evaluation
- `ab-testing-experimentation/holdout-group-analysis/SKILL.md` - Long-term Holdout Group Analysis
- `ab-testing-experimentation/interleaving-experiments/SKILL.md` - Interleaving Recommendation Tests
- `ab-testing-experimentation/pre-post-launch-impact/SKILL.md` - Pre-Post Launch Impact Analysis

### Behavioral Economics & Psychology

- `behavioral-econ/loss-aversion-endowment/SKILL.md` - Loss Aversion & Endowment Analysis
- `behavioral-econ/anchoring-effect-pricing/SKILL.md` - Anchoring Effect in Plan Selection
- `behavioral-econ/scarcity-urgency-impact/SKILL.md` - Scarcity & Urgency Promo Performance
- `behavioral-econ/social-proof-effectiveness/SKILL.md` - Social Proof & Social Signal Conversions
- `behavioral-econ/default-nudge-effect/SKILL.md` - Default Nudge Impact (Autoplay/Shuffle)
- `behavioral-econ/sunk-cost-progression/SKILL.md` - Sunk-Cost Engagement Progression

### Social & Viral

- `social-viral/viral-coefficient-kfactor/SKILL.md` - Viral Coefficient (K-Factor) Calculation
- `social-viral/referral-funnel/SKILL.md` - Referral Funnel Conversion
- `social-viral/social-sharing-behavior/SKILL.md` - Social Sharing & Story Actions
- `social-viral/network-effect-measurement/SKILL.md` - Network Effect Value Analysis
- `social-viral/guild-clan-group-dynamics/SKILL.md` - Shared Playlist Collaborators
- `social-viral/peer-influence-contagion/SKILL.md` - Social Contagion & Peer Influence

### Content & Game Economy

- `content-economy/content-consumption-velocity/SKILL.md` - Content Consumption Velocity
- `content-economy/difficulty-progression-curve/SKILL.md` - Gamified Music Discovery Curves
- `content-economy/economy-sink-source-balance/SKILL.md` - Virtual Tokens & Reward Economy
- `content-economy/loot-reward-distribution/SKILL.md` - Daily Reward & Badge Engagement
- `content-economy/content-gap-analysis/SKILL.md` - Catalog Content Gap Analysis
- `content-economy/level-completion-difficulty-spikes/SKILL.md` - User Level Discovery Barriers

### UX & Product Quality

- `ux-product-quality/heatmaps-scroll-maps/SKILL.md` - UX Heatmaps & Scroll-depth Analytics
- `ux-product-quality/error-crash-impact/SKILL.md` - Playback Error & Crash Impact On Retention
- `ux-product-quality/load-time-engagement-correlation/SKILL.md` - App Load Time vs. Engagement
- `ux-product-quality/accessibility-device-compatibility/SKILL.md` - Device & Operating System Compatibility
- `ux-product-quality/app-rating-review-sentiment/SKILL.md` - App Store Review Sentiment Integration
- `ux-product-quality/support-ticket-clustering/SKILL.md` - Support Ticket NLP Clustering

### Feedback & Sentiment

- `feedback-sentiment/nps-csat-trends/SKILL.md` - Net Promoter Score (NPS) & CSAT Trends
- `feedback-sentiment/in-app-survey-analysis/SKILL.md` - In-App Micro-Survey NLP
- `feedback-sentiment/app-store-review-mining/SKILL.md` - App Store Review Competitor Mining
- `feedback-sentiment/voc-theme-extraction/SKILL.md` - Voice of Customer (VOC) Theme Extraction
- `feedback-sentiment/feature-request-prioritization/SKILL.md` - Feature Request Impact Scoring

### Predictive Modelling

- `predictive-modelling/churn-propensity-scoring/SKILL.md` - User Churn Propensity Scoring
- `predictive-modelling/next-best-action/SKILL.md` - Next-Best-Action Recommendation
- `predictive-modelling/recommendation-engine-performance/SKILL.md` - Curated Playlist Performance Prediction
- `predictive-modelling/early-ltv-prediction/SKILL.md` - Day-7 Customer Lifetime Value Prediction
- `predictive-modelling/anomaly-detection-kpi/SKILL.md` - KPI Anomaly Detection & Volatility Alerts
- `predictive-modelling/propensity-to-purchase/SKILL.md` - Subscription Purchase Propensity Modeling
- `predictive-modelling/user-fatigue-modeling/SKILL.md` - Ad & Push Fatigue Modeling
