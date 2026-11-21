# Final recording and X post

## 90 second recording script

| Time | Operator action | What the judge should see |
| --- | --- | --- |
| 0–10 s | Open the desk on the M4 in Peg drift, frame 8, USDC selected. | “This example treasury holds 100,000 USDC. At $0.993 the indicative difference is $700. Should somebody investigate?” Show the synthetic label. |
| 10–27 s | Scrub to frame 6 (−55 bp), then 7 (−61 bp); return to 8. Copy the brief and open the incident timeline. | First qualifying update warrants a Watch. The next distinct, same-side update confirms an Incident. The timeline shows breach, confirmation, peak, latest evidence and recovery context. |
| 27–39 s | Choose Stale feed, then Recovery. | Unknown samples are visible. Stale USDC loses its estimate; two close-to-peg updates clear the synthetic incident. |
| 39–58 s | Cut to the actual authenticated request code in cmc_client.py, then run `python3 pegscope.py sample --proof`. | Show request URL, query parameters, **HTTP 200**, status timestamp, error code, credit count and a real returned price/update pair together. Frame only the terminal and code. Use the real values on the day. |
| 58–69 s | Switch to Live · Collected quotes and refresh once without running the collector. | Evaluation time advances, latest source capture and chart remain fixed. A new chart point appears only after a new collection. State actual market values, including Normal if that is what the data says. |
| 69–82 s | Run `python3 casefile.py`. | Show the daily low versus close and time of the low for the date printed by the app. Speak the actual measured values. |
| 82–90 s | Show the repo and the offline replay link. | Give the viewer the one-command start and the public URL. |

Record at readable scale. Prepare the key before recording. A screenshot of documentation, a sandbox response, or the synthetic exercise alone cannot establish the live call. If the key fails, fix the issue and re-record the affected segment. Keep the silent preview in the handoff as a rehearsal aid.

## Suggested X post

Built PegScope for stablecoin treasury ops. See when a price move becomes an incident, what it means for a position, and when stale data should stop the estimate.

DoraHacks: [add the published BUIDL URL]
Demo: https://github.com/wesleyhawes/pegscope-cmc-hackathon/blob/main/assets/PegScope-Demo-Preview.mp4
#BuildwithCMC

The current preview contains a real keyless production API call, not an authenticated campaign-key call. If you capture an authenticated call, replace the preview with the final recording and update this post before publishing.

## Publication order

1. Publish the clean public repository and final video under the entrant's chosen accounts. Verify both anonymously. A hosted replay is optional.
2. Create or update the BUIDL and obtain its public, stable project URL. Select **Markets and Trading Tools**. Link the GitHub repository and video, identify the endpoints and include the API feedback.
3. Post the short X draft with the actual BUIDL URL, actual video URL and exact hashtag. Copy the post's permalink into the submission form.
4. Submit the BUIDL to the event, verify its submitted status and open every link logged out. If the form requires a post before final submission, use the BUIDL’s existing public project URL. If the organizer UI will not issue one, use the event Q&A for the supported sequence.
5. Keep the repo and video public through judging, December 10–25. Record the submitted timestamp and final URLs in the entrant’s private release notes.
