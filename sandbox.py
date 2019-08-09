lang = {
    'a': '{a} comes before {b}',
    'b': '{c} is {c} and then {d}',
}

print(lang['a'].format_map({
    'b': 'A',
    'a': 'BBB',
    'c': 'aaa',
}))