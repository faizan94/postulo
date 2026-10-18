// Plain-language copy for the company score, shared by the card badge and the job page.
// Numbers mirror backend/app/scoring/company_score.py; change both together.
import type { CompanyBand } from "@/lib/types";

export const COMPANY_SCORE_WHAT =
  "How actively this company is hiring. It's about the company, not you: your fit is the match %.";

export const COMPANY_BAND_MEANING: Record<CompanyBand, string> = {
  strong: "Hiring actively",
  okay: "Some recent hiring",
  weak: "Little recent hiring",
  not_enough_data: "We can't read this company's job board, so there's no score.",
  pending: "Still checking this company.",
};

export const COMPANY_BANDS_LINE = "Strong 70+ · Okay 40–69 · Weak under 40";

export const COMPANY_SCORE_HOW = [
  "Open roles on their job board: up to 30 points (50 or more gets all 30).",
  "How new their latest job post is: up to 20 points (this week gets all 20, over 3 months gets 0).",
  "A careers site on their own website: up to 20 points.",
  "We add these up and turn them into 0–100. With no own careers site, only the first two count.",
];
