def confirm_move() -> bool:
    answer = input("WARNING: Move mode may remove source files after successful copy. Continue? [y/N]: ")
    return answer.strip().lower() == "y"
