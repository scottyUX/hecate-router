/**
 * People, publications and events for the public lab pages.
 * Photos go in public/people/<slug>.webp (square, ~600px). Members without a
 * photo show their initials. Blurbs are drafts until each member signs off.
 */

export type Person = {
  slug: string;
  name: string;
  role: string;
  affiliation?: string;
  blurb: string;
  photo?: string;
  linkedin?: string;
  website?: string;
};

export type PeopleGroup = { title: string; people: Person[] };

export const PEOPLE: PeopleGroup[] = [
  {
    title: "Principal investigator",
    people: [
      {
        slug: "sagnik-nath",
        name: "Sagnik Nath",
        role: "Assistant Teaching Professor",
        affiliation: "Computer Science & Engineering, UCSC",
        blurb:
          "Leads Hecate Lab. Ph.D. in Electrical Engineering from RPI (2020). Teaches hardware systems and computer architecture, and researches small language models, AI literacy and CS education. Proposed the progress-feature state the lab uses for learned escalation decisions.",
        photo: "/people/sagnik-nath.webp",
        linkedin: "https://www.linkedin.com/in/sagnik-nath-553607a0",
        website: "https://www.sagniknath.com/",
      },
    ],
  },
  {
    title: "Ph.D. student",
    people: [
      {
        slug: "scott-davis",
        name: "Scott Davis",
        role: "Ph.D. student",
        affiliation: "Computer Science & Engineering, UCSC",
        blurb:
          "Leads Hecate’s routing and advisor experiments, from fine-tuned routers to training a small advisor that coaches a cheaper coding agent. Co-founder of 1Shot API and an advisor to Arena.ai.",
      },
    ],
  },
  {
    title: "Master’s students",
    people: [
      {
        slug: "arav-adhikari",
        name: "Arav Adhikari",
        role: "Master’s student",
        affiliation: "UCSC",
        blurb: "Master’s student in Hecate Lab.",
        photo: "/people/arav-adhikari.webp",
        linkedin: "https://www.linkedin.com/in/arav-adhikari/",
      },
      {
        slug: "krishna-kasturi",
        name: "Krishna Kasturi",
        role: "Master’s student",
        affiliation: "UCSC",
        blurb: "Master’s student in Hecate Lab.",
        photo: "/people/krishna-kasturi.webp",
        linkedin: "https://www.linkedin.com/in/krishna-kastur1/",
      },
      {
        slug: "monisha-garika",
        name: "Monisha Garika",
        role: "Master’s student",
        affiliation: "UCSC",
        blurb: "Master’s student in Hecate Lab.",
        photo: "/people/monisha-garika.webp",
        linkedin: "https://www.linkedin.com/in/mg-moni/",
      },
    ],
  },
  {
    title: "Undergraduate researchers",
    people: [
      {
        slug: "jacob-johnston",
        name: "Jacob L. Johnston",
        role: "Undergraduate Research Assistant",
        affiliation: "UCSC",
        blurb: "Undergraduate researcher in Hecate Lab.",
        photo: "/people/jacob-johnston.webp",
        linkedin: "https://www.linkedin.com/in/jacobljohnston/",
      },
      {
        slug: "jaisree-david-ravikumar",
        name: "Jaisree David Ravikumar",
        role: "Undergraduate researcher",
        affiliation: "UCSC",
        blurb: "Undergraduate researcher in Hecate Lab.",
        photo: "/people/jaisree-david-ravikumar.webp",
        linkedin: "https://www.linkedin.com/in/jaisree-david-ravikumar-818799232/",
      },
      {
        slug: "ryan-cleary",
        name: "Ryan Cleary",
        role: "Undergraduate researcher",
        affiliation: "UCSC",
        blurb: "Undergraduate researcher in Hecate Lab.",
      },
    ],
  },
];

export type Publication = {
  title: string;
  authors: string[];
  venue: string;
  year: number;
  type: "Conference" | "Journal" | "Workshop" | "Preprint";
  status?: string;
  topics: string[];
  pdf?: string;
  link?: { label: string; href: string };
};

/** Only work that is public. Anonymized submissions stay off until accepted. */
export const PUBLICATIONS: Publication[] = [];

export type LabEvent = {
  date: string;
  /** ISO date of the first day, for sorting. */
  sortDate: string;
  title: string;
  detail: string;
  place?: string;
};

export const EVENTS: LabEvent[] = [
  {
    date: "Oct 9, 2026",
    sortDate: "2026-10-09",
    title: "AI Pioneer Summit",
    detail: "Talk on self-learning model routing for AI coding agents.",
  },
  {
    date: "Oct 8, 2026",
    sortDate: "2026-10-08",
    title: "Frontier Data Summit",
    detail:
      "Introduced the Hecate Benchmark: fresh, contamination-free web-development tasks drawn from real feature work. Sagnik Nath, Richard Jullig and Scott Davis.",
  },
];
