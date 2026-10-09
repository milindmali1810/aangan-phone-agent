# Vaani (app.vaanivoice.ai) integration notes

Read on 2026-10-09 from https://docs.vaanivoice.ai (index: /llms.txt). The pages were summarised by a small model, so every field name below must be re-checked against `/api-reference/openapi.json` before code depends on it.

## What is documented
- **Auth:** header `X-API-Key: vaani_<key>` on every request. API base `https://api.vaanivoice.ai`.
- **Agent:** has a prompt, language, voice and metadata variables `{like_this}`. `agent_id` is a UUID on the Agent Config page. Per-call overrides via `modify_agent` (persona, training, experience, analysis).
- **Start a call or test:** `POST /api/trigger-call/` with `medium: "webrtc"` returns `token`, `connection_url` (wss, LiveKit), `room_name`, `live_captions_url`. A browser joins with the LiveKit client SDK. `medium: "telephony"` is an outbound phone call.
- **Webhooks:** registered in Settings -> Webhooks (public POST URL, return 200). Events: `call_started`, `user_picked_up_at`, `call_ended`, `call_postprocessing` and others. **`call_postprocessing`** carries `data.transcript`, `data.recording_url`, `data.summary`, `data.entities`, `data.dispositions`, `data.call_duration` (milliseconds), `data.call_id`, `data.room_name`. `call_ended` is flat, has duration in seconds and no transcript.
- **Fetch later:** `GET /api/call_details/{call_id}` (transcription, entity, summary, conversation_eval). Also transcript and audio-stream endpoints.
- **Integrations:** Settings -> Integrations -> Cal.com (paste Cal.com API key, choose an event type); the agent can book during the call.

## Not documented (must test or ask Vaani)
- Webhook signing or authentication, and retries. Plan: secret token in our webhook URL, plus a poll that reconciles any missed calls.
- Cost per minute, and any cost field. Plan: compute voice cost from duration x a rate kept in `aangan/config.py`.
- Whether a WebRTC test call produces a `call_id` that works with the transcript endpoints. Likely linked through `room_name`; to confirm with one real test call.
- Inbound calls and Indian (+91) numbers: the telephony page mentions inbound but only explains outbound setup, and does not confirm Indian numbers can be provisioned.
- Whether the agent can check free slots before booking with Cal.com.
- Webhook event timestamps (needed for time-to-first-response).

## Plan implied by the docs
call ends -> Vaani `call_postprocessing` webhook -> our endpoint -> classifier -> Supabase -> HubSpot -> Telegram -> cost row -> dashboard shows recording + transcript.
