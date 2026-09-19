# Decisions

- **Local Inference**: Huge models (whisper-fa-ct2/model.bin) are deployed alongside the application inside untime/models/ rather than depending on cloud APIs for processing to reduce latency and maintain privacy.
- **Adobe CEP**: Uses ExtendScript to talk to Premiere Pro, a standard albeit older technology for deeply integrating with the timeline.
- **Brand Tokens**: Styles are loaded dynamically from config/brand-tokens.json to allow hot-swapping themes.

*Note: Historical decision records are not present in source; these are inferred from architecture.*
