// tracking.js
// Sends tracker data from the phone/browser to the backend API.

const PawGuardTracking = (() => {
  const CONFIG = {
    // Local FastAPI server for development.
    // Replace with the real server URL later.
    API_URL: 'http://127.0.0.1:8000/api/v1/telemetry/batch',

    // Prototype token for local testing.
    // Replace with a proper device token later.
    API_TOKEN: 'local-dev-token-123',

    // Upload settings
    BATCH_SIZE: 20,
    FLUSH_INTERVAL_MS: 5000,

    // Prevent unlimited local storage growth
    MAX_QUEUE_SIZE: 5000,

    // localStorage key
    QUEUE_KEY: 'pawguard_tracking_queue',

    // Generate a persistent ID for this phone/browser.
    DEVICE_ID:
      localStorage.getItem('pawguard_device_id') ||
      (() => {
        const id = 'phone_' + crypto.randomUUID();

        localStorage.setItem(
          'pawguard_device_id',
          id
        );

        return id;
      })()
  };

  // Local queue of samples waiting to be uploaded
  let queue = [];

  // Automatic upload timer
  let flushTimer = null;

  // Prevent multiple uploads from running at the same time
  let isFlushing = false;


  // ─────────────────────────────────────────────────────────────
  // Queue
  // ─────────────────────────────────────────────────────────────

  function loadQueue() {
    try {
      const stored = localStorage.getItem(
        CONFIG.QUEUE_KEY
      );

      queue = stored
        ? JSON.parse(stored)
        : [];

    } catch (error) {
      console.error(
        'Tracking queue konnte nicht geladen werden:',
        error
      );

      queue = [];
    }
  }


  function saveQueue() {
    try {
      localStorage.setItem(
        CONFIG.QUEUE_KEY,
        JSON.stringify(queue)
      );

    } catch (error) {
      console.error(
        'Tracking queue konnte nicht gespeichert werden:',
        error
      );

      // Keep only the newest samples if storage is full
      queue = queue.slice(-1000);
    }
  }


  // ─────────────────────────────────────────────────────────────
  // Add new tracker sample
  // ─────────────────────────────────────────────────────────────

  function enqueue(sample) {
    queue.push({
      // Data coming from the tracker
      ...sample,

      // Unique ID for duplicate protection on the server
      event_id: crypto.randomUUID(),

      // Client-side timestamps
      timestamp_ms: Date.now(),
      timestamp_iso: new Date().toISOString()
    });


    // Protect against unlimited queue growth
    if (queue.length > CONFIG.MAX_QUEUE_SIZE) {
      queue = queue.slice(-CONFIG.MAX_QUEUE_SIZE);
    }


    // Save locally immediately
    saveQueue();


    // Upload immediately when enough samples are waiting
    if (queue.length >= CONFIG.BATCH_SIZE) {
      flush();
    }
  }


  // ─────────────────────────────────────────────────────────────
  // Upload queue to FastAPI
  // ─────────────────────────────────────────────────────────────

  async function flush() {

    // Do not start another upload while one is running
    if (
      isFlushing ||
      queue.length === 0
    ) {
      return;
    }


    // Wait until the browser reports an internet connection
    if (!navigator.onLine) {
      return;
    }


    isFlushing = true;


    // Upload only a batch
    const batch = queue.slice(
      0,
      CONFIG.BATCH_SIZE
    );


    try {

      const response = await fetch(
        CONFIG.API_URL,
        {
          method: 'POST',

          headers: {
            'Content-Type': 'application/json',
            'Authorization':
              `Bearer ${CONFIG.API_TOKEN}`
          },

          body: JSON.stringify({
            device_id: CONFIG.DEVICE_ID,
            samples: batch
          })
        }
      );


      if (!response.ok) {
        throw new Error(
          `Server antwortete mit HTTP ${response.status}`
        );
      }


      // The server successfully accepted the data.
      // Remove the uploaded samples from the local queue.
      queue.splice(
        0,
        batch.length
      );

      saveQueue();


      console.log(
        `✓ ${batch.length} Tracking-Samples zum Server übertragen`
      );


    } catch (error) {

      console.error(
        'Tracking-Upload fehlgeschlagen:',
        error
      );


      // IMPORTANT:
      // Do NOT remove the samples.
      // They remain in the queue and will be retried later.

    } finally {

      isFlushing = false;
    }
  }


  // ─────────────────────────────────────────────────────────────
  // Start automatic synchronization
  // ─────────────────────────────────────────────────────────────

  function start() {

    // Restore samples from previous sessions
    loadQueue();


    // Try uploading immediately
    flush();


    // Try every few seconds
    flushTimer = setInterval(
      flush,
      CONFIG.FLUSH_INTERVAL_MS
    );


    // Retry automatically when internet returns
    window.addEventListener(
      'online',
      flush
    );
  }


  // ─────────────────────────────────────────────────────────────
  // Stop synchronization
  // ─────────────────────────────────────────────────────────────

  function stop() {

    if (flushTimer) {

      clearInterval(
        flushTimer
      );

      flushTimer = null;
    }
  }


  // ─────────────────────────────────────────────────────────────
  // Debug / status information
  // ─────────────────────────────────────────────────────────────

  function getStatus() {

    return {
      deviceId: CONFIG.DEVICE_ID,

      queuedSamples:
        queue.length,

      online:
        navigator.onLine,

      apiUrl:
        CONFIG.API_URL,

      isFlushing:
        isFlushing
    };
  }


  // ─────────────────────────────────────────────────────────────
  // Public API
  // ─────────────────────────────────────────────────────────────

  return {
    start,
    stop,
    enqueue,
    flush,
    getStatus
  };

})();