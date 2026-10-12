# Everyday - Development Assistance Prompts

**Project:** Everyday book storefront | **Updated:** 12 October 2026

Selected assistance requests, organized by topic and condensed for clarity. This is a summary rather than a verbatim transcript. It covers feature changes, implementation support, design review and explanations.

## 1. Storefront and discovery

Help me improve the existing Everyday storefront with product search, price sorting, stock filtering and clear loading states. Keep the interface consistent with the FastAPI product API.

## 2. Registration and authentication

Help me connect registration and login. Review password hashing, JWT expiry and protected routes. Explain where the logged-in user is verified and how the browser keeps the access token.

## 3. Cart and checkout

Help me connect the bag controls to the signed-in user's cart. Review quantity limits and unavailable products. Save an unpaid order with item snapshots and prevent a retry from creating a duplicate.

## 4. Shopping assistant and policies

Help me connect the shopping assistant to the catalog and cart. Use the store policy PDF for retrieval-based answers with page references. Keep replies within the store's scope and add items only when requested.

## 5. Book scraping and comparison

Reintroduce Books to Scrape using WebBaseLoader and Beautiful Soup. Replace demo titles with matching books and add a Compare price button showing the store price against the source price.

<!-- pagebreak -->

## 6. Comparison through chat

When I explicitly ask the agent to compare a product's price, let it call the comparison tool. When it finds or recommends products, show product cards with a Compare price button so the user can choose to compare.

## 7. Understanding the cache

Explain how comparison caching works, where it is stored and what is used. Clarify when the source is fetched again, what a restart does, and whether store prices are cached too.

## 8. Order information

Let the agent fetch my order history and details of a specific order. Bind the tools to the logged-in user and use saved order information for items, prices, status and shipping address.

## 9. Chat history and sessions

Explain how chat history is managed and sent to the agent. Clarify the message limit, what survives a refresh, and what happens on clearing chat, logout or session expiry.

## 10. Documentation and verification

Update the site poster and low-level design to match the current implementation. Organize assistance prompts with concise headings. Verify the main flows and distinguish completed features from future work.

## Reading this log

Read these requests alongside the source code, low-level design and validation results. The original conversation contains the full wording and follow-up discussion.
