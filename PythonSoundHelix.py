import sys

if "--nogui" in sys.argv[1:]:
    from pathlib import Path
    from app.generator import generate_song, preset_defaults
    preset = "Auto Composer"
    seed = None
    prompt = ""
    language = "English"
    output = str(Path(__file__).resolve().parent / "output")
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == "--preset" and i + 1 < len(argv): preset = argv[i+1]
        if a == "--seed" and i + 1 < len(argv): seed = int(argv[i+1])
        if a == "--output" and i + 1 < len(argv): output = argv[i+1]
        if a == "--prompt" and i + 1 < len(argv): prompt = argv[i+1]
        if a == "--language" and i + 1 < len(argv): language = argv[i+1]
    s = preset_defaults(preset)
    s.prompt = prompt
    s.prompt_language = language
    s.prompt_mode = True
    if seed is not None:
        s.seed = seed
        s.randomize_seed = False
    res = generate_song(s, output)
    print(f"{res.title} | seed={res.seed} | notes={res.note_count}")
    print(res.midi_path)
    raise SystemExit(0)
else:
    from app.main import main
    raise SystemExit(main())
