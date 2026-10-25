# Input formats

All times are finite numeric seconds measured from the start of the source video, including word timestamps. Do not reset word timestamps for each segment or clip.

## Transcript

The transcribe command creates this JSON plus a timestamped `.txt` reading copy. Existing speech tools can supply the same format; extra metadata is ignored. Segments must be ordered and lie inside the video duration. Words are optional; when present they need ordered start/end times within their segment.

```json
{
  "language": "en",
  "segments": [
    {
      "start": 12.1,
      "end": 13.6,
      "text": "Start with the problem.",
      "words": [
        {"start": 12.1, "end": 12.4, "word": "Start"},
        {"start": 12.4, "end": 12.6, "word": "with"},
        {"start": 12.6, "end": 12.8, "word": "the"},
        {"start": 12.8, "end": 13.6, "word": "problem."}
      ]
    }
  ]
}
```

## Editorial plan

```json
{
  "clips": [
    {
      "title": "Start with the problem",
      "start": 12.0,
      "end": 47.2,
      "reason": "A complete explanation with a clear opening and a practical takeaway.",
      "layout": "crop",
      "focus_x": 0.5,
      "post_caption": "A better starting point for your next project."
    }
  ]
}
```

`title`, `start`, and `end` are required. `layout` defaults to `pad` (fit the full source frame with black bars). `crop` fills 9:16 and crops overflow. `focus_x` defaults to 0.5; it positions the crop from left (0) to right (1). It is static, not face tracking. Clip end must be greater than start and not exceed source duration. Each render writes sequential filenames (`clip-001.mp4`), so titles cannot alter output paths. Editorial fields are preserved in the output manifest.

The script deliberately accepts no arbitrary FFmpeg filters, shell commands, or destination filenames in the plan.
