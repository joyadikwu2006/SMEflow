const API_URL = "http://127.0.0.1:8000";

const businessForm = document.getElementById("businessForm");
const message = document.getElementById("message");
const businessList = document.getElementById("businessList");
const productList = document.getElementById("productList");
const productForm = document.getElementById("productForm");
const productMessage = document.getElementById("productMessage");


businessForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const businessName = document.getElementById("businessName").value;
    const businessType = document.getElementById("businessType").value;

    const response = await fetch(`${API_URL}/businesses`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            business_name: businessName,
            business_type: businessType
        })
    });

    const data = await response.json();

    if (response.ok) {
        message.textContent = "Business created successfully!";
        businessForm.reset();
        loadBusinesses();
    } else {
        message.textContent =
            data.detail || "Something went wrong.";
    }
});


async function loadBusinesses() {
    const response = await fetch(`${API_URL}/businesses`);
    const businesses = await response.json();

    businessList.innerHTML = "";

    businesses.forEach(function (business) {
        const div = document.createElement("div");

        div.className = "business";

        div.innerHTML = `
            <h3>${business.business_name}</h3>
            <p>Type: ${business.business_type}</p>
            <p>ID: ${business.id}</p>

            <button onclick="loadProducts(${business.id})">
                View Products
            </button>

            <button onclick="deleteBusiness(${business.id})">
                Delete Business
            </button>
        `;

        businessList.appendChild(div);
    });
}


async function loadProducts(businessId) {
    const response = await fetch(
        `${API_URL}/businesses/${businessId}/products`
    );

    const products = await response.json();

    productList.innerHTML = `<h2>Products</h2>`;

    if (products.length === 0) {
        productList.innerHTML += "<p>No products found.</p>";
        return;
    }

    products.forEach(function (product) {
        productList.innerHTML += `
            <div class="business">
                <h3>${product.name}</h3>
                <p>Price: ₦${product.price}</p>
                <p>Product ID: ${product.id}</p>

                <button onclick="deleteProduct(${businessId}, ${product.id})">
                    Delete Product
                </button>
            </div>
        `;
    });
}


productForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const businessId =
        document.getElementById("productBusinessId").value;

    const productName =
        document.getElementById("productName").value;

    const productPrice =
        document.getElementById("productPrice").value;

    const response = await fetch(
        `${API_URL}/businesses/${businessId}/products`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: productName,
                price: Number(productPrice)
            })
        }
    );

    const data = await response.json();

    if (response.ok) {
        productMessage.textContent =
            "Product created successfully!";

        productForm.reset();

        loadProducts(businessId);
    } else {
        productMessage.textContent =
            data.detail || "Something went wrong.";
    }
});


async function deleteBusiness(businessId) {
    const response = await fetch(
        `${API_URL}/businesses/${businessId}`,
        {
            method: "DELETE"
        }
    );

    const data = await response.json();

    if (response.ok) {
        message.textContent =
            "Business deleted successfully!";

        productList.innerHTML = "";

        loadBusinesses();
    } else {
        message.textContent =
            data.detail || "Something went wrong.";
    }
}


async function deleteProduct(businessId, productId) {
    const response = await fetch(
        `${API_URL}/businesses/${businessId}/products/${productId}`,
        {
            method: "DELETE"
        }
    );

    const data = await response.json();

    if (response.ok) {
        productMessage.textContent =
            "Product deleted successfully!";

        loadProducts(businessId);
    } else {
        productMessage.textContent =
            data.detail || "Something went wrong.";
    }
}