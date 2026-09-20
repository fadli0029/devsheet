{{- $base := .File.ContentBaseName -}}
{{- $fromName := findRE `^\d{4}-\d{2}-\d{2}` $base 1 -}}
---
title: "{{ replace (replaceRE `^\d{4}-\d{2}-\d{2}-` "" $base) "-" " " | title }}"
date: {{ if $fromName }}{{ index $fromName 0 }}{{ else }}{{ dateFormat "2006-01-02" .Date }}{{ end }}
description: ""
draft: true
# tags: ["systems", "c++"]              # indexed by search
# pdf: /pdfs/your-post.pdf              # adds a PDF download link to the header
# github: "https://github.com/you/repo" # adds a GitHub link to the header
---
