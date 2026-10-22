const API_URL = "http://127.0.0.1:8000";

const businessForm = document.getElementById("businessForm");
const message = document.getElementById("message");
const businessList = document.getElementById("businessList");
const productList = document.getElementById("productList");
const productForm = document.getElementById("productForm");
const productMessage = document.getElementById("productMessage");
const productBusinessSelect = document.getElementById("productBusinessId");
const storefrontList = document.getElementById("storefrontList");
const ordersList = document.getElementById("ordersList");
const checkoutForm = document.getElementById("checkoutForm");
const checkoutMessage = document.getElementById("checkoutMessage");
const checkoutProduct = document.getElementById("checkoutProduct");
const ownerAuthPanel = document.getElementById("ownerAuthPanel");
const ownerLoginForm = document.getElementById("ownerLoginForm");
const ownerLoginMessage = document.getElementById("ownerLoginMessage");
const ownerDashboard = document.getElementById("ownerDashboard");

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function getAuthHeaders(extraHeaders = {}) {
    const session = JSON.parse(localStorage.getItem("ownerSession") || "null");
    const token = session && session.token ? session.token : null;

    return {
        ...extraHeaders,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
}

function setMessage(element, text, isError = false) {
    element.textContent = text;
    element.style.color = isError ? "#dc2626" : "#16a34a";
}

function populateBusinessSelect(businesses) {
    const currentValue = productBusinessSelect.value;

    if (productBusinessSelect) {
        productBusinessSelect.innerHTML = '<option value="">Select a business</option>';

        businesses.forEach(function (business) {
            const option = document.createElement("option");
            option.value = business.id;
            option.textContent = `${business.business_name} (${business.business_type})`;
            productBusinessSelect.appendChild(option);
        });

        if (currentValue && businesses.some((business) => String(business.id) === String(currentValue))) {
            productBusinessSelect.value = String(currentValue);
        }
    }
}

function populateCheckoutProducts(products) {
    if (!checkoutProduct) {
        return;
    }

    const currentValue = checkoutProduct.value;
    checkoutProduct.innerHTML = '<option value="">Select a product</option>';

    products.forEach(function (product) {
        const option = document.createElement("option");
        option.value = product.id;
        option.textContent = `${product.name} • ${product.business_name} • ₦${Number(product.price).toLocaleString()}`;
        checkoutProduct.appendChild(option);
    });

    if (currentValue && products.some((product) => String(product.id) === String(currentValue))) {
        checkoutProduct.value = String(currentValue);
    }
}

if (ownerLoginForm) {
    ownerLoginForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const username = document.getElementById("ownerUsername").value.trim();
        const password = document.getElementById("ownerPassword").value.trim();

        try {
            const response = await fetch(`${API_URL}/auth/owner/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem("ownerSession", JSON.stringify(data));
                if (ownerAuthPanel) ownerAuthPanel.style.display = "none";
                if (ownerDashboard) ownerDashboard.classList.remove("hidden");
                setMessage(ownerLoginMessage, "Logged in successfully.");
                await loadBusinesses();
                await loadOrders();
            } else {
                setMessage(ownerLoginMessage, data.detail || "Login failed.", true);
            }
        } catch (error) {
            setMessage(ownerLoginMessage, "Unable to reach the backend.", true);
        }
    });
}

if (businessForm) {
    businessForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const businessName = document.getElementById("businessName").value.trim();
        const businessType = document.getElementById("businessType").value.trim();

        if (!businessName || !businessType) {
            setMessage(message, "Please fill in both business fields.", true);
            return;
        }

        try {
            const response = await fetch(`${API_URL}/businesses`, {
                method: "POST",
                headers: getAuthHeaders({
                    "Content-Type": "application/json"
                }),
                body: JSON.stringify({
                    business_name: businessName,
                    business_type: businessType
                })
            });

            const data = await response.json();

            if (response.ok) {
                setMessage(message, "Business created successfully!");
                businessForm.reset();
                await loadBusinesses();
                await loadStorefront();
            } else {
                setMessage(message, data.detail || "Something went wrong.", true);
            }
        } catch (error) {
            setMessage(message, "Unable to connect to the backend.", true);
        }
    });
}


async function loadStorefront() {
    try {
        const response = await fetch(`${API_URL}/products`);
        const products = await response.json();

        storefrontList.innerHTML = "";
        populateCheckoutProducts(products || []);

        if (!Array.isArray(products) || products.length === 0) {
            storefrontList.innerHTML = "<p class='empty-message'>No products are available in the storefront yet.</p>";
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
                <button type="button" class="secondary-button" onclick="document.getElementById('checkoutProduct').value = ${product.id};">Select Product</button>
            `;

            storefrontList.appendChild(card);
        });
    } catch (error) {
        storefrontList.innerHTML = "<p class='empty-message'>Unable to load the storefront.</p>";
    }
}


async function loadOrders() {
    try {
        const response = await fetch(`${API_URL}/orders`);
        const orders = await response.json();

        ordersList.innerHTML = "";

        if (!Array.isArray(orders) || orders.length === 0) {
            ordersList.innerHTML = "<p class='empty-message'>No orders have been placed yet.</p>";
            return;
        }

        orders.slice().reverse().forEach(function (order) {
            const itemSummary = order.items.map(function (item) {
                return `${item.quantity} x product #${item.product_id}`;
            }).join(", ");

            const div = document.createElement("div");
            div.className = "business";
            div.innerHTML = `
                <h3>Order #${order.id}</h3>
                <p><strong>Customer:</strong> ${escapeHtml(order.customer_name)}</p>
                <p><strong>Email:</strong> ${escapeHtml(order.customer_email)}</p>
                <p><strong>Payment:</strong> ${escapeHtml(order.payment_method)} • ${escapeHtml(order.payment_status)}</p>
                <p><strong>Total:</strong> ₦${Number(order.total_amount).toLocaleString()}</p>
                <p><strong>Items:</strong> ${escapeHtml(itemSummary)}</p>
            `;
            ordersList.appendChild(div);
        });
    } catch (error) {
        ordersList.innerHTML = "<p class='empty-message'>Unable to load orders right now.</p>";
    }
}


async function loadBusinesses() {
    try {
        const response = await fetch(`${API_URL}/businesses`);
        const businesses = await response.json();

        businessList.innerHTML = "";

        if (!Array.isArray(businesses) || businesses.length === 0) {
            businessList.innerHTML = "<p class='empty-message'>No businesses available yet.</p>";
            populateBusinessSelect([]);
            updateDashboardStats();
            return;
        }

        populateBusinessSelect(businesses);

        businesses.forEach(function (business) {
            const div = document.createElement("div");
            div.className = "business";

            div.innerHTML = `
                <div class="business-info">
                    <div>
                        <h3>${escapeHtml(business.business_name)}</h3>
                        <span class="business-type">${escapeHtml(business.business_type)}</span>
                    </div>
                    <span class="business-id">ID: ${business.id}</span>
                </div>

                <div class="business-actions">
                    <button class="view-button" onclick="loadProducts(${business.id})">View Products</button>
                    <button class="edit-button" onclick="editBusiness(${business.id}, '${escapeHtml(business.business_name)}', '${escapeHtml(business.business_type)}')">Edit</button>
                    <button class="delete-button" onclick="deleteBusiness(${business.id})">Delete</button>
                </div>
            `;

            businessList.appendChild(div);
        });

        updateDashboardStats();
        loadOrders();
    } catch (error) {
        businessList.innerHTML = "<p class='empty-message'>Unable to load businesses right now.</p>";
    }
}


async function loadProducts(businessId) {
    try {
        const response = await fetch(`${API_URL}/businesses/${businessId}/products`);
        const products = await response.json();

        productList.innerHTML = "<h2>Products</h2>";

        if (!Array.isArray(products) || products.length === 0) {
            productList.innerHTML += "<p class='empty-message'>No products found for this business.</p>";
            return;
        }

        products.forEach(function (product) {
            productList.innerHTML += `
                <div class="business">
                    <h3>${escapeHtml(product.name)}</h3>
                    <p>Price: ₦${Number(product.price).toLocaleString()}</p>
                    <p>Product ID: ${product.id}</p>
                    <button onclick="editProduct(${businessId}, ${product.id}, '${escapeHtml(product.name)}', ${Number(product.price)})">Edit Product</button>
                    <button onclick="deleteProduct(${businessId}, ${product.id})">Delete Product</button>
                </div>
            `;
        });
    } catch (error) {
        productList.innerHTML = "<p class='empty-message'>Unable to load products right now.</p>";
    }
}


productForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const businessId = productBusinessSelect.value;

    if (!businessId) {
        setMessage(productMessage, "Please select a business first.", true);
        return;
    }

    const productName = document.getElementById("productName").value.trim();
    const productPrice = document.getElementById("productPrice").value;

    if (!productName || !productPrice) {
        setMessage(productMessage, "Please enter a product name and price.", true);
        return;
    }

    try {
        const response = await fetch(`${API_URL}/businesses/${businessId}/products`, {
            method: "POST",
            headers: getAuthHeaders({
                "Content-Type": "application/json"
            }),
            body: JSON.stringify({
                name: productName,
                price: Number(productPrice)
            })
        });

        const data = await response.json();

        if (response.ok) {
            setMessage(productMessage, "Product created successfully!");
            productForm.reset();
            await loadProducts(businessId);
            await loadStorefront();
        } else {
            setMessage(productMessage, data.detail || "Something went wrong.", true);
        }
    } catch (error) {
        setMessage(productMessage, "Unable to connect to the backend.", true);
    }
});


checkoutForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const customerName = document.getElementById("customerName").value.trim();
    const customerEmail = document.getElementById("customerEmail").value.trim();
    const paymentMethod = document.getElementById("paymentMethod").value;
    const productId = checkoutProduct.value;
    const quantity = Number(document.getElementById("checkoutQuantity").value);

    if (!customerName || !customerEmail || !paymentMethod || !productId || quantity <= 0) {
        setMessage(checkoutMessage, "Please complete all checkout details.", true);
        return;
    }

    try {
        const response = await fetch(`${API_URL}/orders`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                customer_name: customerName,
                customer_email: customerEmail,
                payment_method: paymentMethod,
                items: [{
                    product_id: Number(productId),
                    quantity: quantity
                }]
            })
        });

        const data = await response.json();

        if (response.ok) {
            setMessage(checkoutMessage, `Payment successful! Total: ₦${Number(data.total_amount).toLocaleString()}`);
            checkoutForm.reset();
            document.getElementById("checkoutQuantity").value = 1;
            await loadStorefront();
            await updateDashboardStats();
            await loadOrders();
        } else {
            setMessage(checkoutMessage, data.detail || "Checkout failed.", true);
        }
    } catch (error) {
        setMessage(checkoutMessage, "Unable to process payment right now.", true);
    }
});


async function deleteBusiness(businessId) {
    try {
        const response = await fetch(`${API_URL}/businesses/${businessId}`, {
            method: "DELETE",
            headers: getAuthHeaders()
        });

        const data = await response.json();

        if (response.ok) {
            setMessage(message, "Business deleted successfully!");
            productList.innerHTML = "<p class='empty-message'>Select a business to view its products.</p>";
            await loadBusinesses();
        } else {
            setMessage(message, data.detail || "Something went wrong.", true);
        }
    } catch (error) {
        setMessage(message, "Unable to delete this business.", true);
    }
}


async function deleteProduct(businessId, productId) {
    try {
        const response = await fetch(`${API_URL}/businesses/${businessId}/products/${productId}`, {
            method: "DELETE",
            headers: getAuthHeaders()
        });

        const data = await response.json();

        if (response.ok) {
            setMessage(productMessage, "Product deleted successfully!");
            await loadProducts(businessId);
        } else {
            setMessage(productMessage, data.detail || "Something went wrong.", true);
        }
    } catch (error) {
        setMessage(productMessage, "Unable to delete this product.", true);
    }
}


async function editProduct(businessId, productId, currentName, currentPrice) {
    const newName = prompt("Enter the new product name:", currentName);

    if (newName === null) {
        return;
    }

    const newPrice = prompt("Enter the new product price:", currentPrice);

    if (newPrice === null) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/businesses/${businessId}/products/${productId}`, {
            method: "PUT",
            headers: getAuthHeaders({
                "Content-Type": "application/json"
            }),
            body: JSON.stringify({
                name: newName.trim(),
                price: Number(newPrice)
            })
        });

        const data = await response.json();

        if (response.ok) {
            setMessage(productMessage, "Product updated successfully!");
            await loadProducts(businessId);
        } else {
            setMessage(productMessage, data.detail || "Something went wrong.", true);
        }
    } catch (error) {
        setMessage(productMessage, "Unable to update this product.", true);
    }
}

async function editBusiness(businessId, currentName, currentType) {
    const newName = prompt("Enter the new business name:", currentName);

    if (newName === null) {
        return;
    }

    const newType = prompt("Enter the new business type:", currentType);

    if (newType === null) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/businesses/${businessId}`, {
            method: "PUT",
            headers: getAuthHeaders({
                "Content-Type": "application/json"
            }),
            body: JSON.stringify({
                business_name: newName.trim(),
                business_type: newType.trim()
            })
        });

        const data = await response.json();

        if (response.ok) {
            setMessage(message, "Business updated successfully!");
            await loadBusinesses();
        } else {
            setMessage(message, data.detail || "Something went wrong.", true);
        }
    } catch (error) {
        setMessage(message, "Unable to update this business.", true);
    }
}

async function updateDashboardStats() {
    try {
        const businessResponse = await fetch(`${API_URL}/businesses`);
        const businesses = await businessResponse.json();

        let totalProducts = 0;
        let totalValue = 0;

        for (const business of businesses) {
            const productResponse = await fetch(`${API_URL}/businesses/${business.id}/products`);
            const products = await productResponse.json();

            totalProducts += Array.isArray(products) ? products.length : 0;

            if (Array.isArray(products)) {
                products.forEach(function (product) {
                    totalValue += Number(product.price) || 0;
                });
            }
        }

        document.getElementById("businessCount").textContent = businesses.length || 0;
        document.getElementById("productCount").textContent = totalProducts;
        document.getElementById("productValue").textContent = `₦${totalValue.toLocaleString()}`;
    } catch (error) {
        console.error("Could not load dashboard statistics:", error);
    }
}

if (productBusinessSelect) {
    productBusinessSelect.addEventListener("change", function () {
        if (productBusinessSelect.value) {
            loadProducts(productBusinessSelect.value);
        }
    });
}

const savedOwnerSession = localStorage.getItem("ownerSession");
if (ownerDashboard && ownerAuthPanel) {
    if (savedOwnerSession) {
        ownerAuthPanel.style.display = "none";
        ownerDashboard.classList.remove("hidden");
        loadBusinesses();
        loadOrders();
    } else {
        ownerDashboard.classList.add("hidden");
        ownerAuthPanel.style.display = "block";
    }
}

if (businessForm) {
    loadBusinesses();
    loadOrders();
    updateDashboardStats();
}

if (storefrontList) {
    loadStorefront();
}
