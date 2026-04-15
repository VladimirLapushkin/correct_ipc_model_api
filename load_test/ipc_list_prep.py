from pathlib import Path



def main():

    src_dir = Path("lst")
    out_file = Path("txt/ai-ipc.txt")

    values = []

    for lst_file in src_dir.glob("*.LST"):
        with lst_file.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("AI_IPC:"):
                    values.append(line.split("AI_IPC:", 1)[1].strip())
                    break

    c=0
    with out_file.open("w", encoding="utf-8") as f:
        for value in values:
            f.write(value + "\n")
            c+=1
    print(str(c))

if __name__ == "__main__":
    main()