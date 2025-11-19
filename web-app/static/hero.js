// hero.js - simple intersection-based fade-in/out behavior
document.addEventListener('DOMContentLoaded', function () {
  const hero = document.getElementById('hero-section');
  const start = document.getElementById('start-section');
  const recorder = document.getElementById('recorder-section');

  if (!hero) return;

  // ensure start is visible but initially subtle (no hidden class)
  if (start) {
    start.classList.remove('hidden');
    start.classList.remove('fade-in');
    start.classList.remove('fade-out');
  }
  if (recorder) {
    recorder.classList.add('hidden');
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      const id = entry.target.id;

      // observe the hero element to drive the cross-fade into the start-section
      if (id === 'hero-section') {
        const ratio = entry.intersectionRatio;
        // when hero is mostly out of view, fade it out and fade in start
        if (ratio < 0.85) {
          hero.classList.add('fade-out');
          if (start) {
            start.classList.add('fade-in');
            start.classList.remove('fade-out');
          }
        } else {
          // hero mostly visible -> show hero and make start subtle
          hero.classList.remove('fade-out');
          if (start) {
            start.classList.remove('fade-in');
            start.classList.remove('fade-out');
          }
        }
      }

      if (id === 'recorder-section') {
        if (entry.isIntersecting && entry.intersectionRatio > 0.18) {
          // when recorder is scrolled into view: fade it in and fade out hero + previous sections
          recorder.classList.remove('hidden');
          recorder.classList.add('fade-in');
          hero.classList.add('fade-out');
          if (start) start.classList.add('fade-out');
        } else {
          // revert: hide recorder and restore previous sections
          recorder.classList.remove('fade-in');
          recorder.classList.add('hidden');
          hero.classList.remove('fade-out');
          if (start) start.classList.remove('fade-out');
        }
      }
    });
  }, {
    threshold: [0, 0.25, 0.5, 0.75, 0.9, 1]
  });

  // observe hero for cross-fade, and recorder for its own fade
  observer.observe(hero);
  if (recorder) observer.observe(recorder);
});
