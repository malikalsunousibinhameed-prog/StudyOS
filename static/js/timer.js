document.addEventListener("DOMContentLoaded", () => {
    const panel = document.querySelector("[data-timer]");
    if (!panel) return;

    const display = panel.querySelector("[data-timer-display]");
    const status = panel.querySelector("[data-timer-status]");
    const startButton = panel.querySelector("[data-timer-start]");
    const pauseButton = panel.querySelector("[data-timer-pause]");
    const resetButton = panel.querySelector("[data-timer-reset]");
    const sessionForm = panel.querySelector("[data-session-form]");

    const totalSeconds = 25 * 60;
    let remainingSeconds = totalSeconds;
    let endTimestamp = null;
    let intervalId = null;
    let completed = false;

    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainder = seconds % 60;
        return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
    }

    function render() {
        display.textContent = formatTime(remainingSeconds);
        startButton.disabled = Boolean(intervalId) || completed;
        startButton.textContent = remainingSeconds === totalSeconds ? "Start" : "Resume";
        pauseButton.disabled = !intervalId;
        resetButton.disabled = remainingSeconds === totalSeconds && !intervalId && !completed;
    }

    function stopInterval() {
        if (intervalId !== null) {
            window.clearInterval(intervalId);
            intervalId = null;
        }
    }

    function finish() {
        stopInterval();
        remainingSeconds = 0;
        completed = true;
        endTimestamp = null;
        status.textContent = "Your 25-minute session is complete.";
        sessionForm.hidden = false;
        startButton.disabled = true;
        pauseButton.disabled = true;
        resetButton.disabled = false;
        render();
    }

    function tick() {
        if (endTimestamp === null) return;
        remainingSeconds = Math.max(0, Math.ceil((endTimestamp - Date.now()) / 1000));
        if (remainingSeconds <= 0) {
            finish();
            return;
        }
        render();
    }

    startButton.addEventListener("click", () => {
        if (completed || intervalId !== null) return;
        endTimestamp = Date.now() + remainingSeconds * 1000;
        status.textContent = "Focus on one task. You can pause whenever you need.";
        intervalId = window.setInterval(tick, 250);
        tick();
        render();
    });

    pauseButton.addEventListener("click", () => {
        if (intervalId === null) return;
        tick();
        stopInterval();
        endTimestamp = null;
        status.textContent = "Paused. Resume when you're ready.";
        render();
    });

    resetButton.addEventListener("click", () => {
        stopInterval();
        remainingSeconds = totalSeconds;
        endTimestamp = null;
        completed = false;
        sessionForm.hidden = true;
        status.textContent = "Timer reset. Ready when you are.";
        render();
    });

    sessionForm.addEventListener("submit", () => {
        // Prevent accidental repeat clicks while the request is being submitted.
        const submitButton = sessionForm.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = "Recording…";
        }
    });

    render();
});
