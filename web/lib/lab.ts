/**
 * People, publications and events for the public lab pages.
 * Photos go in public/people/<slug>.webp (square, ~600px). Members without a
 * photo show their initials; a `compact` group shows no picture at all.
 * Blurbs are drafts until each member signs off.
 */

export type Person = {
  slug: string;
  name: string;
  role: string;
  affiliation?: string;
  blurb?: string;
  photo?: string;
  /** CSS object-position for the square crop; defaults to centered. */
  photoPosition?: string;
  linkedin?: string;
  website?: string;
};

export type PeopleGroup = { title: string; people: Person[]; compact?: boolean };

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
        photo: "/people/scott-davis.webp",
        photoPosition: "50% 0%",
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
        photo: "/people/arav-adhikari.webp",
        linkedin: "https://www.linkedin.com/in/arav-adhikari/",
      },
      {
        slug: "krishna-kasturi",
        name: "Krishna Kasturi",
        role: "Master’s student",
        affiliation: "UCSC",
        photo: "/people/krishna-kasturi.webp",
        linkedin: "https://www.linkedin.com/in/krishna-kastur1/",
      },
      {
        slug: "monisha-garika",
        name: "Monisha Garika",
        role: "Master’s student",
        affiliation: "UCSC",
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
        photo: "/people/jacob-johnston.webp",
        linkedin: "https://www.linkedin.com/in/jacobljohnston/",
      },
      {
        slug: "jaisree-david-ravikumar",
        name: "Jaisree David Ravikumar",
        role: "Undergraduate researcher",
        affiliation: "UCSC",
        photo: "/people/jaisree-david-ravikumar.webp",
        linkedin: "https://www.linkedin.com/in/jaisree-david-ravikumar-818799232/",
      },
      {
        slug: "ryan-cleary",
        name: "Ryan Cleary",
        role: "Undergraduate researcher",
        affiliation: "UCSC",
        photo: "/people/ryan-cleary.jpg",
      },
    ],
  },
  {
    title: "Research interns",
    compact: true,
    people: [
      { name: "Luna Wang", slug: "luna-wang", affiliation: "Henry M. Gunn High School" },
      { name: "Asin Pancholi", slug: "asin-pancholi", affiliation: "Dougherty Valley High School" },
      { name: "Timothy Tran", slug: "timothy-tran", affiliation: "St. Albans School" },
      { name: "Joshua Cao", slug: "joshua-cao", affiliation: "Monta Vista High School" },
      { name: "Bryan Zhang", slug: "bryan-zhang", affiliation: "The Overlake School" },
    ].map((intern) => ({
      ...intern,
      role: "Research intern",
    })),
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
export const PUBLICATIONS: Publication[] = [
  {
    title:
      "ts-repo-metrics: A Tree-sitter Engine for Cohort-Scale Lexical, Structural, and Cognitive Metrics of TypeScript and React Repositories",
    authors: ["Luna Wang", "Asin Pancholi", "Timothy Tran", "Joshua Cao", "Bryan Zhang", "Scott Davis"],
    venue: "MSR 2027: Data and Tool Showcase Track",
    year: 2027,
    type: "Conference",
    status: "Under review",
    topics: ["Software metrics", "Mining software repositories", "Computing education"],
  },
  {
    title:
      "Cultivating AI Usage Maturity Across the Software Development Lifecycle: An Iterative Course-Design Approach",
    authors: ["Scott Davis"],
    venue:
      "SIGCSE Virtual 2026: 2nd ACM Virtual Global Computing Education Conference, V.2, pp. 554–556",
    year: 2026,
    type: "Conference",
    topics: ["Computing education", "AI-assisted software engineering"],
    link: { label: "ACM DL", href: "https://doi.org/10.1145/3795860.3846212" },
  },
];

export type LabEvent = {
  date: string;
  /** ISO date of the first day, for sorting. */
  sortDate: string;
  title: string;
  detail: string;
  place?: string;
  /** Photo in public/events/, cropped to 4:3; `position` is the CSS object-position. */
  image?: { src: string; alt: string; position?: string };
};

export const EVENTS: LabEvent[] = [
  {
    date: "Oct 9, 2026",
    sortDate: "2026-10-09",
    title: "AI Pioneer Summit",
    detail: "Talk on self-learning model routing for AI coding agents.",
    image: {
      src: "/events/ai-pioneer-summit.jpg",
      alt: "Scott Davis presenting Hecate at the AI Pioneer Summit",
      position: "60% 50%",
    },
  },
  {
    date: "Oct 8, 2026",
    sortDate: "2026-10-08",
    title: "Frontier Data Summit",
    place: "Presented by Snorkel AI",
    detail:
      "Introduced the Hecate Benchmark: fresh, contamination-free web-development tasks drawn from real feature work. Sagnik Nath, Richard Jullig and Scott Davis.",
    image: {
      src: "/events/frontier-data-summit.jpg",
      alt: "Sagnik Nath at the Frontier Data Summit",
      position: "50% 30%",
    },
  },
];
