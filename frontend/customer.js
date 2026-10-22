const API_URL = "http://127.0.0.1:8000";

const customerLoginForm = document.getElementById("customerLoginForm");
const customerLoginMessage = document.getElementById("customerLoginMessage");
const customerDashboard = document.getElementById("customerDashboard");
const customerAuthShell = document.getElementById("customerAuthShell");
const customerAuthPanel = document.getElementById("customerAuthPanel");
const storefrontList = document.getElementById("storefrontList");
const cartItems = document.getElementById("cartItems");
const cartTotal = document.getElementById("cartTotal");
const checkoutForm = document.getElementById("checkoutForm");
const checkoutMessage = document.getElementById("checkoutMessage");
const logoutCustomer = document.getElementById("logoutCustomer");

let cart = [];

function setMessage(element, text, isError = false) {
    element.textContent = text;
    element.style.color = isError ? "#dc2626" : "#16a34a";
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function getAuthHeaders(extraHeaders = {}) {
    try {
        const rawSession = localStorage.getItem("customerSession");
        const session = rawSession ? JSON.parse(rawSession) : null;
        const token = session && session.token ? session.token : null;

        return {
            ...extraHeaders,
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };
    } catch (error) {
        console.error("Could not parse customer session:", error);
        return { ...extraHeaders };
    }
}

function updateCart() {
    cartItems.innerHTML = "";

    if (cart.length === 0) {
        cartItems.innerHTML = "<p class='empty-message'>Your cart is empty.</p>";
        cartTotal.textContent = "₦0";
        return;
    }

    let total = 0;

    cart.forEach(function (item, index) {
        total += Number(item.price) * Number(item.quantity);

        const row = document.createElement("div");
        row.className = "cart-item";
        row.innerHTML = `
            <div>
                <strong>${escapeHtml(item.name)}</strong>
                <p>₦${Number(item.price).toLocaleString()} each</p>
            </div>
            <div class="cart-controls">
                <button type="button" class="mini-button" data-index="${index}" data-action="decrease">-</button>
                <span>${item.quantity}</span>
                <button type="button" class="mini-button" data-index="${index}" data-action="increase">+</button>
            </div>
        `;
        cartItems.appendChild(row);
    });

    cartTotal.textContent = `₦${total.toLocaleString()}`;

    document.querySelectorAll(".mini-button").forEach(function (button) {
        button.addEventListener("click", function () {
            const targetIndex = Number(button.dataset.index);
            const action = button.dataset.action;

            if (action === "increase") {
                cart[targetIndex].quantity += 1;
            } else {
                if (cart[targetIndex].quantity > 1) {
                    cart[targetIndex].quantity -= 1;
                } else {
                    cart.splice(targetIndex, 1);
                }
            }

            updateCart();
        });
    });
}

function addToCart(product) {
    const existing = cart.find((item) => item.id === product.id);

    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({
            id: product.id,
            name: product.name,
            price: Number(product.price),
            quantity: 1,
            business_id: product.business_id,
        });
    }

    updateCart();
}

async function loadStorefront() {
    try {
        const response = await fetch(`${API_URL}/products`);
        const products = await response.json();

        storefrontList.innerHTML = "";

        if (!Array.isArray(products) || products.length === 0) {
            storefrontList.innerHTML = "<p class='empty-message'>No products are available right now.</p>";
            return;
        }

        products.forEach(function (product) {
            const card = document.createElement("div");
            card.className = "storefront-item";
            card.innerHTML = `
                <div class="storefront-header">
                    <h3>${escapeHtml(product.name)}</h3>
                    <span class="product-price">₦${Number(product.price).toLocaleString()}</span>
                </div>
                <p>${escapeHtml(product.business_name)}</p>
                <p>${escapeHtml(product.business_type)}</p>
                <button type="button" class="secondary-button" data-product-id="${product.id}">Add to cart</button>
            `;

            storefrontList.appendChild(card);
        });

        document.querySelectorAll("[data-product-id]").forEach(function (button) {
            button.addEventListener("click", function () {
                const productId = Number(button.dataset.productId);
                const product = products.find((item) => item.id === productId);
                if (product) {
                    addToCart(product);
                }
            });
        });
    } catch (error) {
        storefrontList.innerHTML = "<p class='empty-message'>Unable to load the storefront.</p>";
    }
}

customerLoginForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const username = document.getElementById("customerUsername").value.trim();
    const password = document.getElementById("customerPassword").value.trim();

    try {
        const response = await fetch(`${API_URL}/auth/customer/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            setMessage(customerLoginMessage, "Logged in successfully.");
            customerAuthShell.classList.add("hidden");
            customerAuthPanel.style.display = "none";
            customerDashboard.classList.remove("hidden");
            localStorage.setItem("customerSession", JSON.stringify(data));
            document.getElementById("customerName").value = username;
            await loadStorefront();
        } else {
            setMessage(customerLoginMessage, data.detail || "Login failed.", true);
        }
    } catch (error) {
        setMessage(customerLoginMessage, "Unable to reach the backend.", true);
    }
});

logoutCustomer.addEventListener("click", function () {
    localStorage.removeItem("customerSession");
    customerDashboard.classList.add("hidden");
    customerAuthShell.classList.remove("hidden");
    customerAuthPanel.style.display = "block";
    customerLoginForm.reset();
    setMessage(customerLoginMessage, "You have been logged out.");
    cart = [];
    updateCart();
});

async function finalizeCheckoutFromSavedState() {
    const pendingCheckout = JSON.parse(localStorage.getItem("pendingCheckout") || "null");
    if (!pendingCheckout) {
        return;
    }

    try {
        const orderResponse = await fetch(`${API_URL}/orders`, {
            method: "POST",
            headers: getAuthHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({
                customer_name: pendingCheckout.customer_name,
                customer_email: pendingCheckout.customer_email,
                payment_method: pendingCheckout.payment_method || "stripe",
                items: pendingCheckout.items,
            }),
        });

        const orderData = await orderResponse.json();
        if (orderResponse.ok) {
            setMessage(checkoutMessage, `Payment successful! Total: ₦${Number(orderData.total_amount).toLocaleString()}`);
            localStorage.removeItem("pendingCheckout");
            cart = [];
            updateCart();
            checkoutForm.reset();
            await loadStorefront();
        }
    } catch (error) {
        console.error("Could not finalize checkout state:", error);
    }
}

checkoutForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    if (cart.length === 0) {
        setMessage(checkoutMessage, "Add at least one product to the cart.", true);
        return;
    }

    const customerName = document.getElementById("customerName").value.trim();
    const customerEmail = document.getElementById("customerEmail").value.trim();
    const paymentMethod = document.getElementById("paymentMethod").value;
    const normalizedPaymentMethod = paymentMethod === "card" ? "stripe" : paymentMethod;

    if (!customerName || !customerEmail || !paymentMethod) {
        setMessage(checkoutMessage, "Please fill in customer details and payment method.", true);
        return;
    }

    const payload = {
        customer_name: customerName,
        customer_email: customerEmail,
        items: cart.map((item) => ({
            product_id: item.id,
            quantity: item.quantity,
        })),
    };

    const totalAmount = cart.reduce((sum, item) => sum + Number(item.price) * Number(item.quantity), 0);

    try {
        if (normalizedPaymentMethod === "stripe") {
            const paymentResponse = await fetch(`${API_URL}/payments/create-checkout-session`, {
                method: "POST",
                headers: getAuthHeaders({ "Content-Type": "application/json" }),
                body: JSON.stringify(payload),
            });

            const paymentData = await paymentResponse.json();

            if (!paymentResponse.ok) {
                setMessage(checkoutMessage, paymentData.detail || "Stripe checkout failed.", true);
                return;
            }

            if (paymentData.url) {
                localStorage.setItem(
                    "pendingCheckout",
                    JSON.stringify({
                        customer_name: customerName,
                        customer_email: customerEmail,
                        payment_method: "stripe",
                        items: payload.items,
                    }),
                );
                window.location.href = paymentData.url;
                return;
            }
        }

        const paymentResponse = await fetch(`${API_URL}/payments/create-intent`, {
            method: "POST",
            headers: getAuthHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({
                amount: totalAmount,
                currency: "NGN",
                customer_email: customerEmail,
            }),
        });

        const paymentData = await paymentResponse.json();

        if (!paymentResponse.ok) {
            setMessage(checkoutMessage, paymentData.detail || "Payment failed.", true);
            return;
        }

        const orderResponse = await fetch(`${API_URL}/orders`, {
            method: "POST",
            headers: getAuthHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({
                customer_name: customerName,
                customer_email: customerEmail,
                payment_method: paymentMethod,
                items: payload.items,
            }),
        });

        const orderData = await orderResponse.json();

        if (orderResponse.ok) {
            setMessage(checkoutMessage, `Payment successful! Total: ₦${Number(orderData.total_amount).toLocaleString()}`);
            cart = [];
            updateCart();
            checkoutForm.reset();
            await loadStorefront();
        } else {
            setMessage(checkoutMessage, orderData.detail || "Checkout failed.", true);
        }
    } catch (error) {
        console.error("Checkout error:", error);
        setMessage(checkoutMessage, error instanceof Error ? error.message : "Unable to process payment right now.", true);
    }
});

const savedCustomerSession = localStorage.getItem("customerSession");
if (savedCustomerSession) {
    customerAuthShell.classList.add("hidden");
    customerAuthPanel.style.display = "none";
    customerDashboard.classList.remove("hidden");
    loadStorefront();
}

const checkoutState = new URLSearchParams(window.location.search).get("checkout");
if (checkoutState === "success") {
    localStorage.removeItem("pendingCheckout");
    setMessage(checkoutMessage, "Payment completed successfully. Your order is being processed.");
} else if (checkoutState === "cancelled") {
    localStorage.removeItem("pendingCheckout");
    setMessage(checkoutMessage, "Checkout was cancelled. Your cart is still available.", true);
}

updateCart();
