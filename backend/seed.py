from sqlalchemy.orm import Session
from .models import AnalysisDefinition, KPIDefinition

ANALYSIS_CATALOG = [
    # Group 1: Acquisition & Onboarding
    {
        "group_key": "acquisition-onboarding",
        "group_name": "Acquisition & Onboarding",
        "agent_id": "acquisition-analyst",
        "skills": [
            {"key": "channel-attribution", "name": "Channel Attribution Analysis", "desc": "Determine which marketing and signup channels drive the highest quality users."},
            {"key": "install-to-registration-conversion", "name": "Install-to-Registration Conversion", "desc": "Measure friction and drop-off rates between initial app load and successful user registration."},
            {"key": "ftue-funnel", "name": "First-Time User Experience (FTUE) Funnel", "desc": "Step-by-step funnel analysis of the very first session to locate setup bottlenecks."},
            {"key": "onboarding-completion-dropoff", "name": "Onboarding Completion Drop-off", "desc": "Identify where users abandon the onboarding flow prior to first music play."},
            {"key": "time-to-first-value", "name": "Time-to-First-Value (TTFV)", "desc": "Calculate duration and user actions required before a user experiences the core product value (first full song play)."},
            {"key": "source-medium-quality", "name": "Source/Medium Quality Analysis", "desc": "Compare user cohorts from Google, Meta, referral, organic, etc., on long-term value metrics."}
        ]
    },
    # Group 2: Engagement & Usage Patterns
    {
        "group_key": "engagement-patterns",
        "group_name": "Engagement & Usage Patterns",
        "agent_id": "engagement-analyst",
        "skills": [
            {"key": "dau-wau-mau-stickiness", "name": "DAU/WAU/MAU Stickiness", "desc": "Track active user stickiness ratios to monitor product habituation and daily usage frequency."},
            {"key": "session-frequency-duration-depth", "name": "Session Frequency, Duration & Depth", "desc": "Detailed analysis of how often users listen, for how long, and how many tracks per session."},
            {"key": "feature-adoption-heatmap", "name": "Feature Adoption Heatmap", "desc": "Monitor user interaction across playlists, search, lyrics, library, and sharing."},
            {"key": "power-vs-casual-segmentation", "name": "Power vs. Casual User Segmentation", "desc": "Classify users into engagement bands to analyze what triggers transition to power user status."},
            {"key": "time-of-day-day-of-week-usage", "name": "Usage by Time-of-Day & Day-of-Week", "desc": "Isolate listening spikes (commutes, weekends, sleep hours) to optimize push notification delivery."},
            {"key": "session-interval", "name": "Session Interval (Time-Between-Sessions)", "desc": "Measure elapsed time between consecutive listening sessions to locate friction or decay."},
            {"key": "content-screen-consumption", "name": "Content & Screen Consumption", "desc": "Analyze which UI screens (Home, Artist Profile, Playlist details) drive the most play events."},
            {"key": "navigation-path-flow-sankey", "name": "Navigation Path Flow (Sankey)", "desc": "Visual flow mapping of user clicks leading up to a subscription checkout or play click."},
            {"key": "dead-end-rage-tap", "name": "Dead-End & Rage Tap Analysis", "desc": "Surface un-clickable or slow UI elements causing user frustration and quick exits."}
        ]
    },
    # Group 3: Retention & Churn
    {
        "group_key": "retention-churn",
        "group_name": "Retention & Churn",
        "agent_id": "retention-analyst",
        "skills": [
            {"key": "cohort-retention-curves", "name": "Cohort Retention Curves", "desc": "Plot daily, weekly, and monthly active user retention curves for tracking cohort health."},
            {"key": "rolling-vs-classic-retention", "name": "Rolling vs. Classic Retention", "desc": "Compare strict day-N retention vs. rolling active calculations for better baseline metrics."},
            {"key": "churn-prediction-survival", "name": "Churn Prediction & Survival Analysis", "desc": "Model user lifecycle decay curves to estimate probability of user churn over time."},
            {"key": "resurrection-analysis", "name": "Resurrected User Analysis", "desc": "Evaluate why lapsed users return and what actions (push alerts, emails, friends) brought them back."},
            {"key": "retention-by-segment", "name": "Retention by User Segment", "desc": "Compare retention curves across age groups, signup countries, genres, and subscription tiers."},
            {"key": "n-day-activity-curves", "name": "N-Day Activity Curves", "desc": "Analyse the probability of a user staying active after exactly N days of continuous app usage."},
            {"key": "magic-number-analysis", "name": "Magic Number Engagement Analysis", "desc": "Determine if completing a specific action (e.g., adding 5 tracks to a playlist) drives a step-change in retention."}
        ]
    },
    # Group 4: Monetization & Revenue
    {
        "group_key": "monetization-revenue",
        "group_name": "Monetization & Revenue",
        "agent_id": "monetization-analyst",
        "skills": [
            {"key": "arpu-arppu-arpdau", "name": "ARPU / ARPPU / ARPDAU Metrics", "desc": "Analyze revenue per user, per paying user, and daily active user to track commercial viability."},
            {"key": "conversion-to-payer-funnel", "name": "Conversion-to-Payer Funnel", "desc": "Trace the path from free sign-up to premium subscription purchase to optimize pricing gates."},
            {"key": "time-to-first-purchase", "name": "Time-to-First-Purchase Duration", "desc": "How long does a free tier user wait before upgrading to premium subscription?"},
            {"key": "rfm-purchase-recency", "name": "Recency, Frequency, Monetary (RFM) Purchase Analysis", "desc": "Segment payers by purchasing behavior to target promotional discount offerings."},
            {"key": "revenue-concentration-whale-curve", "name": "Revenue Concentration (Whale Curve)", "desc": "Identify what percentage of aggregate subscription or ad revenue is driven by a small hyper-engaged cohort."},
            {"key": "price-sensitivity-elasticity", "name": "Price Sensitivity & Elasticity Modeling", "desc": "Observe subscription upgrade rates across different geographic pricing brackets."},
            {"key": "sku-item-sales", "name": "SKU & In-App Item Sales", "desc": "Analyze purchases of specific tier add-ons, merch, or ticket items where available."},
            {"key": "ltv-modeling", "name": "Lifetime Value (LTV) Modeling", "desc": "Predict the long-term cumulative net revenue generated by an average user cohort."},
            {"key": "ltv-to-cac-by-channel", "name": "LTV-to-CAC Ratio by Acquisition Channel", "desc": "Compare customer acquisition cost against customer lifetime value across social, search, and referral sources."},
            {"key": "subscription-renewal-cancellation", "name": "Subscription Renewal & Cancellation Patterns", "desc": "Examine payment failures, churn notices, and cancellation survey inputs to locate exit drivers."},
            {"key": "trial-to-paid-conversion", "name": "Trial-to-Paid Conversion Optimization", "desc": "Analyze the conversion rate of 7-day or 30-day premium free trials into paying subscriptions."},
            {"key": "iap-basket-analysis", "name": "In-App Purchases Basket Analysis", "desc": "Examine correlation between multiple add-on services or virtual items bought together."}
        ]
    },
    # Group 5: Funnel & Conversion
    {
        "group_key": "funnel-conversion",
        "group_name": "Funnel & Conversion",
        "agent_id": "funnel-analyst",
        "skills": [
            {"key": "multi-step-conversion-funnel", "name": "Multi-Step Conversion Funnel", "desc": "Track multi-screen checkout processes to target friction zones and leaks."},
            {"key": "micro-conversion-tracking", "name": "Micro-Conversion Tracking", "desc": "Analyze minor conversions (like clicking 'View Premium Plans') that predict subscription upgrade."},
            {"key": "funnel-stage-dropoff", "name": "Funnel Stage Drop-off Metrics", "desc": "Examine the timing and triggers of funnel drops (app backgrounding, back clicks)."},
            {"key": "funnel-comparison-by-segment", "name": "Funnel Comparison by Segment", "desc": "Compare checkout funnel performance across countries, devices, and genders."},
            {"key": "cart-checkout-abandonment", "name": "Cart & Checkout Abandonment Analysis", "desc": "Drill down into users who entered the payment details screen but failed to click 'Pay Now'."},
            {"key": "paywall-hit-rate-conversion", "name": "Paywall Hit Rate & Conversion", "desc": "Examine how often free users hit paywall gates and the immediate upgrade success rate."}
        ]
    },
    # Group 6: Segmentation & Personas
    {
        "group_key": "segmentation-personas",
        "group_name": "Segmentation & Personas",
        "agent_id": "segmentation-analyst",
        "skills": [
            {"key": "behavioral-clustering", "name": "Behavioral Clustering Analysis", "desc": "Apply unsupervised clustering to segment users by musical taste, skip behavior, and time of day."},
            {"key": "rfm-segmentation", "name": "RFM Segment Profiling", "desc": "Analyze user recency, frequency, and duration of sessions to build standard engagement classes."},
            {"key": "psychographic-segmentation", "name": "Genre-Taste Profile Mapping", "desc": "Deduce underlying user mood profiles (Chill, Party, Focused, High Energy) based on track acoustic tags."},
            {"key": "lifecycle-stage-segmentation", "name": "User Lifecycle Stage Analysis", "desc": "Profile users by active months: Newbies, Retained Steady, Churn-risk, Reactivated."},
            {"key": "motivational-segmentation", "name": "Motivational Segment Profiling", "desc": "Group users based on core music utilities: Social Sharers, Background Listeners, Hardcore Collectors."},
            {"key": "high-value-user-profiling", "name": "High-Value User Profiling", "desc": "Examine common acquisition paths, demographic profiles, and taste metrics of the top 5% of paying users."}
        ]
    },
    # Group 7: A/B Testing & Experimentation
    {
        "group_key": "ab-testing-experimentation",
        "group_name": "A/B Testing & Experimentation",
        "agent_id": "experimentation-analyst",
        "skills": [
            {"key": "controlled-experiment-analysis", "name": "Controlled Experiment (A/B Test) Analysis", "desc": "Evaluate test variant performance using t-tests and chi-squared tests to calculate statistical significance."},
            {"key": "multi-armed-bandit-optimization", "name": "Multi-Armed Bandit Evaluation", "desc": "Analyze live reward rates of dynamic traffic-allocating bandit algorithms for promo banners."},
            {"key": "holdout-group-analysis", "name": "Long-term Holdout Group Analysis", "desc": "Examine macro-effects of UI features withheld from a control cohort for months (e.g., ad density changes)."},
            {"key": "interleaving-experiments", "name": "Interleaving Recommendation Tests", "desc": "Fast evaluation of recommendations algorithm variations by presenting combined listings directly to users."},
            {"key": "pre-post-launch-impact", "name": "Pre-Post Launch Impact Analysis", "desc": "Use difference-in-differences or synthetic control methods to evaluate features rolled out without an A/B test."}
        ]
    },
    # Group 8: Behavioral Economics & Psychology
    {
        "group_key": "behavioral-econ",
        "group_name": "Behavioral Economics & Psychology",
        "agent_id": "behavioral-econ-analyst",
        "skills": [
            {"key": "loss-aversion-endowment", "name": "Loss Aversion & Endowment Analysis", "desc": "Evaluate upgrade conversion of users who built extensive custom playlists during a free Premium trial."},
            {"key": "anchoring-effect-pricing", "name": "Anchoring Effect in Plan Selection", "desc": "Examine how showcasing the Family/Duo tier impacts the checkout conversion of the Individual Premium plan."},
            {"key": "scarcity-urgency-impact", "name": "Scarcity & Urgency Promo Performance", "desc": "Measure conversion uplift from countdown timers on holiday subscription discounts."},
            {"key": "social-proof-effectiveness", "name": "Social Proof & Social Signal Conversions", "desc": "Track conversion lift of paywalls that display 'Joined by 50,000 others in your country'."},
            {"key": "default-nudge-effect", "name": "Default Nudge Impact (Autoplay/Shuffle)", "desc": "Examine how default playlist play configurations impact long-term session lengths and engagement metrics."},
            {"key": "sunk-cost-progression", "name": "Sunk-Cost Engagement Progression", "desc": "Analyze if paying an annual upfront subscription vs. monthly plans increases daily listen minutes."}
        ]
    },
    # Group 9: Social & Viral
    {
        "group_key": "social-viral",
        "group_name": "Social & Viral",
        "agent_id": "social-viral-analyst",
        "skills": [
            {"key": "viral-coefficient-kfactor", "name": "Viral Coefficient (K-Factor) Calculation", "desc": "Measure invitation loops and conversion rate of newly referred contacts."},
            {"key": "referral-funnel", "name": "Referral Funnel Conversion", "desc": "Track the invitation lifecycle: Sent -> Clicked -> Installed -> Signed Up."},
            {"key": "social-sharing-behavior", "name": "Social Sharing & Story Actions", "desc": "Analyze which songs or playlists are shared most to external apps (Instagram, WhatsApp) and subsequent referral traffic."},
            {"key": "network-effect-measurement", "name": "Network Effect Value Analysis", "desc": "Examine if users with connected active friends have higher retention and subscription probability."},
            {"key": "guild-clan-group-dynamics", "name": "Shared Playlist Collaborators", "desc": "Analyze engagement trends inside collaborative, multi-user playlists."},
            {"key": "peer-influence-contagion", "name": "Social Contagion & Peer Influence", "desc": "Evaluate if a user adopting a new artist/genre predicts their connected friends adopting the same artist."}
        ]
    },
    # Group 10: Content & Game Economy
    {
        "group_key": "content-economy",
        "group_name": "Content & Game Economy",
        "agent_id": "economy-analyst",
        "skills": [
            {"key": "content-consumption-velocity", "name": "Content Consumption Velocity", "desc": "Track how quickly users consume newly released albums, and how fast enthusiasm decays."},
            {"key": "difficulty-progression-curve", "name": "Gamified Music Discovery Curves", "desc": "Measure drop-off rates inside recommendation quests, daily mixes, or musical trivia mini-games."},
            {"key": "economy-sink-source-balance", "name": "Virtual Tokens & Reward Economy", "desc": "Analyze earn-to-spend ratios of discoveries or loyalty points redeemed for artist items."},
            {"key": "loot-reward-distribution", "name": "Daily Reward & Badge Engagement", "desc": "Examine click-through and return rates on daily discovery badges (e.g., 'Early Listener')."},
            {"key": "content-gap-analysis", "name": "Catalog Content Gap Analysis", "desc": "Identify search keywords that return zero results or high exit rates (missing artists/songs)."},
            {"key": "level-completion-difficulty-spikes", "name": "User Level Discovery Barriers", "desc": "Pinpoint barriers where users abandon progression loops or curated taste challenges."}
        ]
    },
    # Group 11: UX & Product Quality
    {
        "group_key": "ux-product-quality",
        "group_name": "UX & Product Quality",
        "agent_id": "ux-quality-analyst",
        "skills": [
            {"key": "heatmaps-scroll-maps", "name": "UX Heatmaps & Scroll-depth Analytics", "desc": "Evaluate user scrolling and clicking patterns inside the home screen feed layout."},
            {"key": "error-crash-impact", "name": "Playback Error & Crash Impact On Retention", "desc": "Correlate audio buffer errors or application crashes to immediate active churn."},
            {"key": "load-time-engagement-correlation", "name": "App Load Time vs. Engagement", "desc": "Quantify retention and session depth decay as app startup or track loading latency increases."},
            {"key": "accessibility-device-compatibility", "name": "Device & Operating System Compatibility", "desc": "Flag performance drops (crashes, latency, dropouts) on specific mobile device architectures."},
            {"key": "app-rating-review-sentiment", "name": "App Store Review Sentiment Integration", "desc": "Ingest and analyze negative app store ratings to highlight UX pain points."},
            {"key": "support-ticket-clustering", "name": "Support Ticket NLP Clustering", "desc": "Group incoming customer service requests to highlight immediate product defects."}
        ]
    },
    # Group 12: Feedback & Sentiment
    {
        "group_key": "feedback-sentiment",
        "group_name": "Feedback & Sentiment",
        "agent_id": "feedback-analyst",
        "skills": [
            {"key": "nps-csat-trends", "name": "Net Promoter Score (NPS) & CSAT Trends", "desc": "Track quantitative customer satisfaction indicators and correlate them to active retention rates."},
            {"key": "in-app-survey-analysis", "name": "In-App Micro-Survey NLP", "desc": "Analyze open-ended user feedback prompted immediately after specific actions (e.g. cancellation, downgrade)."},
            {"key": "app-store-review-mining", "name": "App Store Review Competitor Mining", "desc": "Analyze review keywords of competitor music platforms to spot feature opportunities."},
            {"key": "voc-theme-extraction", "name": "Voice of Customer (VOC) Theme Extraction", "desc": "Aggregate user forums, support emails, and surveys to flag trending complaints and feature requests."},
            {"key": "feature-request-prioritization", "name": "Feature Request Impact Scoring", "desc": "Rank requested items by matching requester user-profiles against total business value / paying metrics."}
        ]
    },
    # Group 13: Predictive Modelling
    {
        "group_key": "predictive-modelling",
        "group_name": "Predictive Modelling",
        "agent_id": "predictive-analyst",
        "skills": [
            {"key": "churn-propensity-scoring", "name": "User Churn Propensity Scoring", "desc": "Calculate probability of a user churning in the next 7 days based on recent usage decay and skip rates."},
            {"key": "next-best-action", "name": "Next-Best-Action Recommendation", "desc": "Predict the next optimal user touchpoint (push, promo, genre recommendation) to maximize long-term retention."},
            {"key": "recommendation-engine-performance", "name": "Curated Playlist Performance Prediction", "desc": "Evaluate play-through and retention metrics of algorithmic vs. human curated discovery lists."},
            {"key": "early-ltv-prediction", "name": "Day-7 Customer Lifetime Value Prediction", "desc": "Predict a user's 365-day LTV based on their initial 7 days of active listening patterns."},
            {"key": "anomaly-detection-kpi", "name": "KPI Anomaly Detection & Volatility Alerts", "desc": "Engine that monitors and flags statistical trend breaks or spikes in core subscription or active cohorts."},
            {"key": "propensity-to-purchase", "name": "Subscription Purchase Propensity Modeling", "desc": "Score active free users by their upgrade likelihood to optimize targeting of paywall discount campaigns."},
            {"key": "user-fatigue-modeling", "name": "Ad & Push Fatigue Modeling", "desc": "Predict threshold of ad frequency or push notifications that trigger app uninstallation."}
        ]
    }
]

INITIAL_KPIS = [
    {
        "metric": "dau",
        "name": "Daily Active Users (DAU)",
        "description": "Total unique users active on the platform on a given day.",
        "current_value": 7254.0,
        "previous_value": 7320.0,
        "status": "green",
        "baseline_window": 7,
        "threshold_warning": 0.05,
        "threshold_critical": 0.10,
        "schedule": "daily",
        "sparkline_data": [7120.0, 7150.0, 7280.0, 7310.0, 7400.0, 7320.0, 7254.0]
    },
    {
        "metric": "new_user_activation",
        "name": "New User Activation Rate",
        "description": "Percentage of newly registered users who complete a full song listening event on Day 1.",
        "current_value": 0.824,
        "previous_value": 0.812,
        "status": "green",
        "baseline_window": 7,
        "threshold_warning": 0.04,
        "threshold_critical": 0.08,
        "schedule": "daily",
        "sparkline_data": [0.795, 0.801, 0.798, 0.815, 0.810, 0.812, 0.824]
    },
    {
        "metric": "arpdau",
        "name": "Average Revenue Per Daily Active User (ARPDAU)",
        "description": "Average subscription-proportional revenue generated by daily active users (USD).",
        "current_value": 0.284,
        "previous_value": 0.312,
        "status": "warning",
        "baseline_window": 14,
        "threshold_warning": 0.05,
        "threshold_critical": 0.12,
        "schedule": "daily",
        "sparkline_data": [0.320, 0.315, 0.318, 0.310, 0.305, 0.312, 0.284]
    },
    {
        "metric": "d1_retention",
        "name": "D1 Retention Rate",
        "description": "Percentage of active users returning exactly 1 day after a session.",
        "current_value": 0.785,
        "previous_value": 0.791,
        "status": "green",
        "baseline_window": 7,
        "threshold_warning": 0.03,
        "threshold_critical": 0.06,
        "schedule": "daily",
        "sparkline_data": [0.792, 0.788, 0.795, 0.790, 0.794, 0.791, 0.785]
    },
    {
        "metric": "d7_retention",
        "name": "D7 Retention Rate",
        "description": "Percentage of active users returning exactly 7 days after a session.",
        "current_value": 0.542,
        "previous_value": 0.584,
        "status": "critical",
        "baseline_window": 14,
        "threshold_warning": 0.04,
        "threshold_critical": 0.07,
        "schedule": "daily",
        "sparkline_data": [0.590, 0.585, 0.592, 0.588, 0.580, 0.584, 0.542]
    },
    {
        "metric": "skip_rate",
        "name": "Overall Track Skip Rate",
        "description": "Percentage of all playback events ended before 30 seconds or explicitly skipped.",
        "current_value": 0.222,
        "previous_value": 0.221,
        "status": "green",
        "baseline_window": 7,
        "threshold_warning": 0.05,
        "threshold_critical": 0.10,
        "schedule": "daily",
        "sparkline_data": [0.218, 0.220, 0.224, 0.221, 0.219, 0.221, 0.222]
    }
]

def seed_database(db: Session):
    # Check if analysis definitions exist
    if db.query(AnalysisDefinition).count() == 0:
        print("Seeding Analysis Definitions into SQLite DB...")
        for group in ANALYSIS_CATALOG:
            for skill in group["skills"]:
                db_def = AnalysisDefinition(
                    key=skill["key"],
                    name=skill["name"],
                    description=skill["desc"],
                    group_key=group["group_key"],
                    group_name=group["group_name"],
                    agent_id=group["agent_id"],
                    default_config={"date_range": "30d"}
                )
                db.add(db_def)
        db.commit()

    # Check if KPIs exist
    if db.query(KPIDefinition).count() == 0:
        print("Seeding Initial KPI Definitions into SQLite DB...")
        for kpi in INITIAL_KPIS:
            db_kpi = KPIDefinition(
                metric=kpi["metric"],
                name=kpi["name"],
                description=kpi["description"],
                current_value=kpi["current_value"],
                previous_value=kpi["previous_value"],
                status=kpi["status"],
                baseline_window=kpi["baseline_window"],
                threshold_warning=kpi["threshold_warning"],
                threshold_critical=kpi["threshold_critical"],
                schedule=kpi["schedule"],
                sparkline_data=kpi["sparkline_data"]
            )
            db.add(db_kpi)
        db.commit()
