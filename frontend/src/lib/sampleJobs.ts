import type { ExperienceLevel } from "../types/api";

/**
 * Example job descriptions so a new visitor can try CareerForge in one click.
 * Generic roles written for this app, not real postings or companies. Skill
 * names match the skills dictionary so they're recognised exactly.
 */
export interface SampleJob {
  id: string;
  title: string;
  company: string;
  experience_level: ExperienceLevel;
  description: string;
  required_skills: string[];
  preferred_skills: string[];
}

const COMPANY = "Sample job (example)";

export const SAMPLE_JOBS: SampleJob[] = [
  {
    id: "python-developer",
    title: "Junior Python Developer",
    company: COMPANY,
    experience_level: "entry",
    description: `Junior Python Developer (example posting)

We're looking for a fresher or junior developer to build and maintain backend services.

Requirements
- Python and Django (or Django REST Framework)
- SQL with PostgreSQL
- Building REST APIs
- Git

Nice to have
- Docker
- AWS
- pytest`,
    required_skills: ["Python", "Django", "Django REST Framework", "PostgreSQL", "SQL", "REST APIs", "Git"],
    preferred_skills: ["Docker", "AWS", "pytest"],
  },
  {
    id: "frontend-developer",
    title: "Frontend Developer (React)",
    company: COMPANY,
    experience_level: "entry",
    description: `Frontend Developer, React (example posting)

Build responsive, accessible web interfaces with our design team.

Requirements
- JavaScript and TypeScript
- React
- HTML and CSS
- Git

Nice to have
- Tailwind CSS
- Next.js
- Jest`,
    required_skills: ["JavaScript", "TypeScript", "React", "HTML", "CSS", "Git"],
    preferred_skills: ["Tailwind CSS", "Next.js", "Jest"],
  },
  {
    id: "full-stack-developer",
    title: "Full-Stack Developer",
    company: COMPANY,
    experience_level: "entry",
    description: `Full-Stack Developer (example posting)

Work across the stack: React frontend, Python or Node.js backend, relational database.

Requirements
- React and JavaScript
- Python or Node.js
- REST APIs
- SQL databases (PostgreSQL or MySQL)
- Git

Nice to have
- Docker
- CI/CD
- TypeScript`,
    required_skills: ["React", "JavaScript", "Python", "Node.js", "REST APIs", "SQL", "PostgreSQL", "Git"],
    preferred_skills: ["Docker", "CI/CD", "TypeScript"],
  },
  {
    id: "data-analyst",
    title: "Data Analyst (Fresher)",
    company: COMPANY,
    experience_level: "entry",
    description: `Data Analyst, fresher (example posting)

Turn business data into clear reports and dashboards.

Requirements
- SQL
- Microsoft Excel
- Python with Pandas
- Data Analysis

Nice to have
- Power BI or Tableau
- Matplotlib`,
    required_skills: ["SQL", "Microsoft Excel", "Python", "Pandas", "Data Analysis"],
    preferred_skills: ["Power BI", "Tableau", "Matplotlib"],
  },
  {
    id: "ml-intern",
    title: "Machine Learning Intern",
    company: COMPANY,
    experience_level: "internship",
    description: `Machine Learning Intern (example posting)

Help build and evaluate machine learning models.

Requirements
- Python
- Machine Learning fundamentals
- NumPy and Pandas
- scikit-learn

Nice to have
- PyTorch or TensorFlow
- Natural Language Processing
- Git`,
    required_skills: ["Python", "Machine Learning", "NumPy", "Pandas", "scikit-learn"],
    preferred_skills: ["PyTorch", "TensorFlow", "Natural Language Processing", "Git"],
  },
  {
    id: "java-developer",
    title: "Java Backend Developer",
    company: COMPANY,
    experience_level: "entry",
    description: `Java Backend Developer (example posting)

Develop backend services and APIs.

Requirements
- Java
- Spring Boot
- REST APIs
- SQL (MySQL or PostgreSQL)
- Object-Oriented Programming

Nice to have
- Microservices
- Docker
- JUnit`,
    required_skills: ["Java", "Spring Boot", "REST APIs", "SQL", "MySQL", "Object-Oriented Programming"],
    preferred_skills: ["Microservices", "Docker", "JUnit"],
  },
];

export function findSampleJob(id: string | null): SampleJob | undefined {
  return id ? SAMPLE_JOBS.find((s) => s.id === id) : undefined;
}
