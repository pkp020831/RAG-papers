const form = document.querySelector("#search-form");
const input = document.querySelector("#query");
const results = document.querySelector("#results");
const summary = document.querySelector("#result-summary");
const template = document.querySelector("#result-template");

const fieldNames = { title: "제목", keywords: "키워드", metadata: "메타데이터", text: "추출 본문" };

function renderResult(paper, query) {
  const card = template.content.cloneNode(true);
  card.querySelector(".document-id").textContent = paper.id;
  card.querySelector(".score").textContent = query ? `BM25 ${paper.score.toFixed(2)}` : "컬렉션 문서";
  card.querySelector("h2").textContent = paper.title;
  card.querySelector(".authors").textContent = paper.authors.join(" · ");
  card.querySelector(".venue").textContent = paper.venue || paper.document_status;
  card.querySelector(".abstract").textContent = paper.preview || "텍스트를 추출하지 못한 PDF입니다. 파일명과 내장 메타데이터로만 검색할 수 있습니다.";
  const tags = card.querySelector(".keywords");
  paper.keywords.forEach((keyword) => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = keyword;
    tags.append(tag);
  });
  card.querySelector(".match-info").textContent = query && paper.matched_fields.length
    ? `일치: ${paper.matched_fields.map((field) => fieldNames[field]).join(" · ")}`
    : paper.document_status;
  const link = card.querySelector(".pdf-link");
  link.href = paper.pdf_url;
  results.append(card);
}

async function search(query = "") {
  results.replaceChildren();
  summary.textContent = "검색 중…";
  try {
    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error("검색 요청 실패");
    const data = await response.json();
    if (!data.results.length) {
      results.innerHTML = `<p class="empty"><strong>일치하는 논문이 없습니다.</strong><br />다른 키워드로 다시 검색해 보세요.</p>`;
      summary.textContent = `“${query}” 검색 결과 0편`;
      return;
    }
    data.results.forEach((paper) => renderResult(paper, query));
    summary.textContent = query ? `“${query}” 검색 결과 ${data.count}편` : `전체 컬렉션 ${data.count}편`;
  } catch (error) {
    results.innerHTML = `<p class="empty">검색기를 불러오지 못했습니다. 서버가 실행 중인지 확인해 주세요.</p>`;
    summary.textContent = "연결 오류";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  search(input.value.trim());
});
document.querySelectorAll("[data-query]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.query;
    search(input.value);
  });
});

search();
