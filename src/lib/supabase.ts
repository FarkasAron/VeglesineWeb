import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export type Problem = {
  id: string;
  year: number;
  exam_type: "kozep" | "emelt";
  exam_session: string;
  exam_part: string | null;
  problem_number: number;
  sub_part: string | null;
  problem_image_url: string | null;
  max_points: number | null;
  difficulty_level: "konnyu" | "kozepes" | "nehez" | null;
  topic_tags: string[];
  ocr_used: boolean;
};

export const TOPIC_LABELS: Record<string, string> = {
  halmazok:               "Halmazok",
  logika:                 "Matematikai logika",
  kombinatorika:          "Kombinatorika",
  grafelmelet:            "Gráfelmélet",
  valoszinuseg:           "Valószínűség-számítás",
  statisztika:            "Statisztika",
  "szamok-muveletek":     "Számok és műveletek",
  szamrendszerek:         "Számrendszerek",
  szamelmelet:            "Számelmélet",
  algebra:                "Algebra",
  egyenletek:             "Egyenletek és egyenlőtlenségek",
  fuggvenyek:             "Függvények és grafikonok",
  exponencialis:          "Exponenciális és logaritmikus függvények",
  trigonometria:          "Trigonometria",
  sorozatok:              "Sorozatok",
  "penzugyi-matematika":  "Pénzügyi matematika",
  "geometria-sik":        "Síkgeometria",
  "geometria-ter":        "Térgeometria",
  "koordinata-geometria": "Koordinátageometria",
  vektorok:               "Vektorok",
  transzformacio:         "Geometriai transzformációk",
  hatarertek:             "Határérték és folytonosság",
  differencialszamitas:   "Differenciálszámítás",
  integralszamitas:       "Integrálszámítás",
  bizonyitasok:           "Bizonyítások és elmélet",
  szovegfeladas:          "Szöveges feladat",
};

export const DIFFICULTY_LABELS: Record<string, string> = {
  konnyu:  "Könnyű",
  kozepes: "Közepes",
  nehez:   "Nehéz",
};
