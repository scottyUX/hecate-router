const stages = document.querySelectorAll(".stage");

if (stages.length && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        entry.target.classList.toggle("is-visible", entry.isIntersecting);
      }
    },
    { rootMargin: "-20% 0px -55% 0px", threshold: 0.2 }
  );

  stages.forEach((stage) => observer.observe(stage));
}
