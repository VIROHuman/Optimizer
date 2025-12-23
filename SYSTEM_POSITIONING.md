# System Positioning & Product Boundaries

## 🎯 Core Positioning

**This is a route-level transmission line feasibility optimizer for pre-engineering decision support.**

This tool is NOT a member-level structural design engine and must NOT attempt to compete with PLS-CADD.

## 🔴 HARD PRODUCT BOUNDARIES (NON-NEGOTIABLE)

### What This System Does NOT Do

- ❌ Member-level optimization
- ❌ Angle-by-angle steel sizing
- ❌ Finite Element Method (FEM) analysis
- ❌ Buckling mode solving
- ❌ Full multi-span cable equilibrium
- ❌ Broken wire case analysis (advisory only)
- ❌ Longitudinal load redistribution

### What This System Does

- ✅ Route-level feasibility assessment
- ✅ Cost-optimized but conservative outputs
- ✅ Explains why costs are high
- ✅ Avoids engineering theatre
- ✅ Hands off cleanly to detailed design tools
- ✅ Corridor selection support
- ✅ Early-stage budgeting
- ✅ Risk budgeting

## 📊 Accuracy Target

**±25-30% accuracy target for feasibility/DPR-stage estimates.**

This is appropriate for:
- Corridor selection
- Early-stage budgeting
- Risk assessment
- Engineering effort planning

This is NOT appropriate for:
- Detailed design
- Construction contracts
- Member-level specifications

## 🧱 Key Calibrations

### Steel Weight Calibration (FIX 1)

Steel weights are calibrated using Tower Efficiency Factors:
- Suspension: 0.65 (35% reduction)
- Angle/Tension: 0.75 (25% reduction)
- Dead-end: 0.85 (15% reduction)

**This is calibration, not design.** We're adjusting for known over-estimation in geometry-based calculations.

### Foundation Classification (FIX 4)

Foundations are **classified**, not designed:
- Based on soil, terrain, slope, water proximity
- Returns foundation class, confidence, cost multiplier
- **Foundation costs are indicative and classification-based**

### Ruling Span Approximation (FIX 3)

Ruling span is **approximated**, not fully solved:
- Groups suspension towers into strain sections
- Computes equivalent ruling span: Sr = sqrt(sum(L_i^3) / sum(L_i))
- **Full multi-span equilibrium is not solved**

## 🌍 Geography, Codes & Currency

**Location is NEVER user-typed. Always derived from route geometry.**

- India → IS + INR
- USA → ASCE/NESC + USD
- Europe → Eurocode + EUR

Currency is presentation-only. No FX conversion unless approved source exists.

## 📊 Output Reframing

### Removed

- ❌ "Industry norm deviation"
- ❌ Any competitive comparison with PLS-CADD
- ❌ Claims of "engineering comparable to PLS-CADD"

### Added

- ✅ Cost Context (Indicative): Primary cost drivers, terrain contribution, ROW contribution, foundation uncertainty
- ✅ Disclaimers: "This tool supports corridor selection, budgeting, and early feasibility. Detailed engineering requires dedicated structural analysis software."
- ✅ Positioning: "This system operates upstream of detailed design tools."

## 🧠 Confidence Score

Confidence must be explained, not decorative.

**Drivers:**
- Terrain resolution
- Soil assumption quality
- Wind source
- Route definition quality
- Foundation classification certainty

**Never exceed 85% without:**
- Survey-grade terrain
- Geotech inputs

## ✅ Final Acceptance Criteria

After all fixes are applied:

- ✅ Steel weights drop 20-35% (still conservative)
- ✅ Spans are non-uniform where terrain demands
- ✅ Foundations are classified, not faked
- ✅ Currency & codes never mismatch geography
- ✅ Output is credible in a feasibility meeting
- ✅ No one mistakes this for PLS-CADD

## 🧠 Internal Positioning

**This system operates upstream of detailed design tools.**

It narrows corridors, budgets risk, and guides engineering effort.

**Every output must be explainable in plain engineering language.**

**Explicitly position outputs as FEASIBILITY / DPR-STAGE.**

